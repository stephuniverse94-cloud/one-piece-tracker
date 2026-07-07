#!/usr/bin/env python3
"""
One Piece TCG price tracker — hoofdscript.

Gebruik:
    python main.py              # normale run, checkt alle enabled shops
    python main.py --shop dracoon   # test 1 shop (handig bij debuggen)
    python main.py --dry-run    # print resultaten, stuur niks naar Discord
    python main.py --status     # toon de HUIDIGE prijs bij elke shop voor je
                                 # hele watchlist, los van prijsgrenzen — stuurt
                                 # nooit iets naar Discord en raakt de state niet aan

Zie README.md voor hoe je dit elke 30 minuten laat draaien.
"""

import argparse
import sys
import time

import config
import state
import discord_notify
from matcher import classify_and_match, is_english, double_pack_code_fallback
from scrapers import shopify, generic


CATEGORY_THRESHOLDS = {
    "booster_pack": lambda: config.BOOSTER_PACK_ALERT_PRICE,
    "booster_box": lambda: config.BOOSTER_BOX_ALERT_PRICE,
    "double_pack": lambda: config.DOUBLE_PACK_ALERT_PRICE,
}


def _code_label_for(category: str, watch_item: dict) -> str:
    if category == "double_pack":
        return f"Vol. {watch_item['vol']}"
    return watch_item["code"]  # booster_pack of booster_box


def _is_priority(category: str, code_label: str, dp_fallback: dict) -> bool:
    """OP-09 en EB-03 (config.PRIORITY_CODES) mogen altijd bovenaan de
    melding staan, ongeacht productsoort. Bij Double Packs kijken we naar de
    OP-code die volgens jouw watchlist bij dat Vol.-nummer hoort (zie
    matcher.double_pack_code_fallback)."""
    if category == "double_pack":
        vol = int(code_label.replace("Vol. ", ""))
        code = dp_fallback.get(vol)
    else:
        code = code_label
    return code in config.PRIORITY_CODES


def scrape_shop(shop: dict) -> list[dict]:
    if shop["platform"] == "shopify":
        return shopify.scrape(shop)
    return generic.scrape(shop)


def run(target_shop_id: str | None = None, dry_run: bool = False, status: bool = False):
    st = state.load_state()
    shops_to_check = [
        s for s in config.SHOPS
        if s["enabled"] and (target_shop_id is None or s["id"] == target_shop_id)
    ]

    if not shops_to_check:
        print(f"Geen (enabled) shop gevonden voor id={target_shop_id!r}")
        sys.exit(1)

    # --status raakt nooit de state aan en stuurt nooit iets naar Discord —
    # het is puur een momentopname voor in de terminal.
    write_state = not dry_run and not status
    send_to_discord = not dry_run and not status

    all_hits = []          # alles wat deze run onder de grens zit én op voorraad is
    status_rows = []       # ALLE matches, ongeacht prijs/voorraad (voor --status)
    restocks = []
    still_active_keys = set()
    failed_shops = []
    persistent_failure_shops = []
    total_products_seen = 0
    # Per shop: hoeveel watchlist-matches gevonden, en hoeveel daarvan op voorraad.
    # Gebruiken we aan het eind om shops te melden waar ALLES uitverkocht is.
    shop_match_stats = {}  # shop_name -> {"matched": int, "in_stock": int}
    dp_fallback = double_pack_code_fallback(config.DOUBLE_PACKS, config.BOOSTER_PACKS)

    for shop in shops_to_check:
        print(f"[*] {shop['name']} ({shop['country']})...")
        try:
            products = scrape_shop(shop)
        except Exception as e:
            print(f"  [!] Onverwachte fout bij {shop['name']}: {e}")
            products = []

        success = bool(products)
        if write_state:
            streak = state.record_shop_result(st, shop["id"], success=success)
            if not success and state.is_persistent_failure(streak):
                persistent_failure_shops.append(f"{shop['name']} ({streak}x op rij)")

        if not success:
            failed_shops.append(shop["name"])
            continue

        total_products_seen += len(products)
        stats = shop_match_stats.setdefault(shop["name"], {"matched": 0, "in_stock": 0})

        for product in products:
            category, watch_item = classify_and_match(
                product["title"], config.BOOSTER_PACKS, config.DOUBLE_PACKS
            )
            if category is None:
                continue
            if not is_english(product["title"]):
                continue  # alleen Engelstalige kaarten, geen JP/FR/DE/KR/CN

            lo, hi = config.PRICE_SANITY_RANGES[category]
            if not (lo <= product["price"] <= hi):
                print(f"  [!] {shop['name']}: '{product['title']}' matcht als {category} "
                      f"maar kost €{product['price']:.2f} — buiten het realistische bereik "
                      f"(€{lo:.0f}-€{hi:.0f}), waarschijnlijk een verkeerde match. Genegeerd.")
                continue

            code_label = _code_label_for(category, watch_item)
            in_stock_now = product.get("in_stock", True)

            # Restock-melding: los van prijs.
            stock_key = state.make_key(shop["id"], category, code_label)
            if not status and state.is_restock(st, stock_key, in_stock_now):
                restocks.append({
                    **product, "category": category, "code_label": code_label,
                    "set_name": watch_item["name"],
                })
            if write_state:
                state.update_stock(st, stock_key, in_stock_now)

            stats["matched"] += 1

            if status:
                status_rows.append({
                    **product, "category": category, "code_label": code_label,
                    "set_name": watch_item["name"],
                })
                continue  # --status filtert niet op prijs/voorraad, gewoon alles tonen

            if not in_stock_now:
                continue  # uitverkocht: geen link, geen melding — telt wel mee voor de "alles uitverkocht"-check
            stats["in_stock"] += 1

            threshold = CATEGORY_THRESHOLDS[category]()
            if product["price"] >= threshold:
                continue  # boven de grens, geen deal

            key = state.make_key(shop["id"], category, code_label)
            still_active_keys.add(key)

            price_key = f"{category}|{code_label}"
            is_record = state.check_and_update_lowest(st, price_key, product["price"]) if write_state else False

            hit = {
                **product,
                "category": category,
                "code_label": code_label,
                "set_name": watch_item["name"],
                "alert_price": threshold,
                "priority": _is_priority(category, code_label, dp_fallback),
                "is_record": is_record,
            }
            all_hits.append(hit)

            if state.should_alert(st, key, product["price"]):
                state.record_alert(st, key, product["price"])
                hit["_is_new_alert"] = True

        print(f"  -> {len(products)} producten gezien, "
              f"{sum(1 for h in all_hits if h['shop'] == shop['name'])} match(es) onder de grens")

    if status:
        _print_status(status_rows)
        return

    # Shops waar we watchlist-producten vonden, maar echt he-le-maal geen enkele
    # op voorraad was (i.p.v. gewoon te duur — dat is geen "uitverkocht"-geval).
    sold_out_shops = [
        name for name, s in shop_match_stats.items()
        if s["matched"] > 0 and s["in_stock"] == 0
    ]

    # Prioriteitssets (config.PRIORITY_CODES) altijd bovenaan, verder op prijs.
    all_hits.sort(key=lambda h: (not h["priority"], h["price"]))
    new_hits = [h for h in all_hits if h.get("_is_new_alert")]

    print()
    print(f"Klaar. {total_products_seen} producten bekeken over {len(shops_to_check)} shop(s).")
    print(f"{len(all_hits)} actieve deal(s) onder de prijsgrens, waarvan {len(new_hits)} nieuw/verder gezakt.")
    if restocks:
        print(f"{len(restocks)} restock(s) gedetecteerd (los van prijs).")
    if failed_shops:
        print(f"Kon niet checken: {', '.join(failed_shops)}")
    if sold_out_shops:
        print(f"Alles uitverkocht bij: {', '.join(sold_out_shops)}")
    if persistent_failure_shops:
        print(f"Al langere tijd stuk: {', '.join(persistent_failure_shops)}")

    for h in new_hits:
        marker = "\u2b50 " if h["priority"] else "  "
        record = " \U0001f3c6 laagste ooit gezien!" if h["is_record"] else ""
        print(f"  {marker}NIEUW: [{h['shop']}] {h['code_label']} {h['set_name']} — €{h['price']:.2f}{record} — {h['url']}")

    if write_state:
        state.clear_stale(st, still_active_keys)
        newly_out = state.newly_sold_out(st, sold_out_shops)
        state.update_sold_out(st, sold_out_shops)
        state.save_state(st)

    if send_to_discord:
        discord_notify.send_deals(new_hits)
        discord_notify.send_restocks(restocks)
        # Stuur alleen een fout-samenvatting als er ECHT meerdere shops
        # faalden (1 shop die soms hapert is niet alarmerend genoeg voor
        # een aparte Discord-melding).
        if len(failed_shops) >= 3:
            discord_notify.send_error_summary(failed_shops)
        if newly_out:
            discord_notify.send_sold_out_summary(newly_out)
        if persistent_failure_shops:
            discord_notify.send_persistent_failure_summary(persistent_failure_shops)
    elif not status:
        print("\n(--dry-run: state en Discord-melding overgeslagen)")


def _print_status(rows: list[dict]):
    """Nette terminal-tabel voor --status: alles wat gevonden is, gegroepeerd
    per set, ongeacht prijs of voorraad."""
    if not rows:
        print("Niks van je watchlist gevonden bij de gecheckte shop(s).")
        return

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        label = f"{r['code_label']} — {r['set_name']} ({r['category']})"
        grouped.setdefault(label, []).append(r)

    print(f"\n=== Status: {len(rows)} matches over {len(grouped)} set(s) ===\n")
    for label, items in sorted(grouped.items()):
        print(label)
        for it in sorted(items, key=lambda x: x["price"]):
            voorraad = "op voorraad" if it.get("in_stock", True) else "UITVERKOCHT"
            print(f"    €{it['price']:>7.2f}  {voorraad:<12}  [{it['shop']}]  {it['url']}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="One Piece TCG price tracker")
    parser.add_argument("--shop", help="Alleen deze shop-id checken (zie config.py)")
    parser.add_argument("--dry-run", action="store_true", help="Niks naar Discord/state schrijven")
    parser.add_argument("--status", action="store_true",
                         help="Toon huidige prijzen voor je hele watchlist, los van prijsgrenzen. "
                              "Stuurt nooit naar Discord en raakt de state niet aan.")
    args = parser.parse_args()

    start = time.time()
    run(target_shop_id=args.shop, dry_run=args.dry_run, status=args.status)
    print(f"\nDuur: {time.time() - start:.1f}s")

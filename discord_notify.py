"""Stuurt een Discord-melding via webhook wanneer er nieuwe deals gevonden zijn."""

import requests
import config

MAX_FIELDS_PER_EMBED = 25  # Discord-limiet


def _price_line(hit: dict) -> str:
    record = " 🏆" if hit.get("is_record") else ""
    return f"**€{hit['price']:.2f}**{record} — [{hit['shop']}]({hit['url']})"


def send_deals(new_hits: list[dict]):
    """new_hits: lijst van dicts met keys: title, price, url, shop, category,
    code_label, set_name, alert_price, priority."""
    if not config.DISCORD_WEBHOOK_URL:
        print("[!] Geen DISCORD_WEBHOOK_URL ingesteld — melding wordt overgeslagen.")
        return
    if not new_hits:
        return

    # Prioriteitssets (config.PRIORITY_CODES, bv. OP-09 & EB-03) krijgen een
    # eigen melding die als EERSTE verstuurd wordt — dus als eerste in het
    # kanaal te zien, los van welke productsoort het is. Ze verschijnen niet
    # nogmaals in de gewone categorie-meldingen hieronder.
    priority_hits = [h for h in new_hits if h["priority"]]
    regular_hits = [h for h in new_hits if not h["priority"]]

    embeds = []
    if priority_hits:
        label = ", ".join(config.PRIORITY_CODES)
        embeds.append(_build_embed(f"⭐ Prioriteit ({label})", priority_hits, 0xE84393))

    category_sections = [
        ("booster_pack", "🔥 Booster Packs onder de prijsgrens", 0xE0A526),
        ("booster_box", "🔥 Booster Boxes onder de prijsgrens", 0x27AE60),
        ("double_pack", "🔥 Double Packs onder de prijsgrens", 0x2596BE),
    ]
    for category, title, color in category_sections:
        items = [h for h in regular_hits if h["category"] == category]
        if items:
            embeds.append(_build_embed(title, items, color))

    for embed in embeds:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)
        if resp.status_code >= 300:
            print(f"[!] Discord webhook gaf status {resp.status_code}: {resp.text[:300]}")


def _build_embed(title: str, hits: list[dict], color: int) -> dict:
    # Groepeer per set/vol zodat je in 1 oogopslag ziet welke shops goedkoop zijn
    grouped: dict[str, list[dict]] = {}
    for h in hits:
        label = f"{h['code_label']} — {h['set_name']}"
        grouped.setdefault(label, []).append(h)

    fields = []
    for label, group in list(grouped.items())[:MAX_FIELDS_PER_EMBED]:
        group.sort(key=lambda h: h["price"])
        lines = [_price_line(h) for h in group[:6]]  # niet te lang per veld
        fields.append({"name": label, "value": "\n".join(lines), "inline": False})

    return {
        "title": title,
        "color": color,
        "fields": fields,
        "footer": {"text": "One Piece TCG price tracker"},
    }


def send_error_summary(failed_shops: list[str]):
    """Optioneel: laat weten welke shops deze run niet gecheckt konden worden."""
    if not config.DISCORD_WEBHOOK_URL or not failed_shops:
        return
    embed = {
        "title": "⚠️ Sommige shops konden niet gecheckt worden",
        "description": "\n".join(f"- {s}" for s in failed_shops),
        "color": 0x999999,
    }
    requests.post(config.DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)


def send_sold_out_summary(sold_out_shops: list[str]):
    """Shops waar we watchlist-producten vonden, maar ECHT helemaal niks van
    op voorraad was (i.p.v. gewoon te duur). Wordt maar 1x gemeld per shop —
    zolang de shop uitverkocht blijft, komt dit niet elke run terug."""
    if not config.DISCORD_WEBHOOK_URL or not sold_out_shops:
        return
    embed = {
        "title": "📭 Alles uitverkocht bij deze shops",
        "description": "\n".join(f"- {s}" for s in sold_out_shops),
        "color": 0x555555,
        "footer": {"text": "Je krijgt dit maar 1x te zien zolang dit zo blijft"},
    }
    requests.post(config.DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)


def send_restocks(restocks: list[dict]):
    """Melding los van prijs: dit item was uitverkocht en is weer beschikbaar.
    Handig voor schaarse sets waar 'weer te koop' belangrijker is dan de prijs."""
    if not config.DISCORD_WEBHOOK_URL or not restocks:
        return

    grouped: dict[str, list[dict]] = {}
    for r in restocks:
        label = f"{r['code_label']} — {r['set_name']}"
        grouped.setdefault(label, []).append(r)

    fields = []
    for label, group in list(grouped.items())[:MAX_FIELDS_PER_EMBED]:
        group.sort(key=lambda h: h["price"])
        lines = [f"€{r['price']:.2f} — [{r['shop']}]({r['url']})" for r in group[:6]]
        fields.append({"name": label, "value": "\n".join(lines), "inline": False})

    embed = {
        "title": "🔔 Weer op voorraad (ongeacht prijs)",
        "color": 0x9B59B6,
        "fields": fields,
        "footer": {"text": "One Piece TCG price tracker"},
    }
    requests.post(config.DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)


def send_persistent_failure_summary(entries: list[str]):
    """Een shop faalt niet zomaar 1 keer, maar al meerdere runs op rij —
    dat wijst eerder op een kapotte URL/selector dan een tijdelijk hikje."""
    if not config.DISCORD_WEBHOOK_URL or not entries:
        return
    embed = {
        "title": "🛠️ Deze shop(s) lijken al langere tijd stuk",
        "description": "\n".join(f"- {e}" for e in entries)
        + "\n\nCheck de Actions-log en zie README 'Een shop repareren'.",
        "color": 0xC0392B,
    }
    requests.post(config.DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)

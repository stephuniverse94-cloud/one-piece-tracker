"""
Scraper voor Shopify-shops (PocketGames, RareCards, OPTCG, Outpost Brussels,
TcgReus, PremiumCardSupply).

Elke Shopify-collectiepagina heeft een verborgen JSON-endpoint:
    https://shop.nl/collections/one-piece/products.json

Dat geeft gestructureerde data terug (titel, prijs per variant, handle) zonder
dat we HTML hoeven te parsen. Veel betrouwbaarder dan scrapen — breekt niet als
de shop een nieuw thema/design kiest.
"""

from scrapers.utils import get_session, polite_sleep, get_with_retry
import config

MAX_PAGES = 5  # met limit=250 per pagina zou 1 al bijna altijd genoeg moeten
               # zijn voor een niche-categorie, maar voor de zekerheid checken
               # we door tot 5 pagina's als een shop toch heel veel producten heeft.


def scrape(shop: dict) -> list[dict]:
    """Retourneert een lijst van {title, price, url, shop, in_stock} voor een Shopify-shop."""
    session = get_session()
    results = []

    for collection_url in shop["urls"]:
        base = collection_url.split("/collections/")[0]
        seen_handles = set()

        for page in range(1, MAX_PAGES + 1):
            json_url = collection_url.rstrip("/") + f"/products.json?limit=250&page={page}"
            try:
                resp = get_with_retry(session, json_url, timeout=config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"  [!] {shop['name']}: kon {json_url} niet ophalen ({e})")
                polite_sleep()
                break

            raw_products = data.get("products", [])
            if not raw_products:
                if page == 1:
                    print(f"  [!] {shop['name']}: {json_url} gaf 0 producten terug — "
                          f"waarschijnlijk klopt de collection-naam in de URL niet (meer)")
                break  # geen producten meer op deze pagina -> geen volgende pagina proberen

            new_this_page = 0
            for product in raw_products:
                handle = product.get("handle", "")
                if handle in seen_handles:
                    continue  # shops geven soms dezelfde producten terug bij een niet-ondersteunde pagina
                seen_handles.add(handle)
                new_this_page += 1

                title = product.get("title", "")
                product_url = f"{base}/products/{handle}"

                variants = product.get("variants", [])
                all_prices = [float(v["price"]) for v in variants if v.get("price") is not None]
                in_stock_prices = [
                    float(v["price"])
                    for v in variants
                    if v.get("available") and v.get("price") is not None
                ]
                if not all_prices:
                    continue

                # We geven ook uitverkochte producten door (met in_stock=False) i.p.v.
                # ze hier al weg te gooien — main.py gebruikt dat om je nooit een link
                # naar iets uitverkochts te sturen, maar wel te kunnen zien of een shop
                # het setje wél verkoopt (alleen even niet op voorraad).
                results.append(
                    {
                        "title": title,
                        "price": min(in_stock_prices) if in_stock_prices else min(all_prices),
                        "url": product_url,
                        "shop": shop["name"],
                        "in_stock": bool(in_stock_prices),
                    }
                )

            polite_sleep()

            if new_this_page == 0:
                break  # volgende pagina herhaalt alleen maar wat we al hadden

    return results

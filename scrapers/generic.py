"""
Generieke scraper voor alle shops die geen Shopify draaien (WooCommerce,
OpenCart, Magento, Wix, en een paar custom platforms zoals Intertoys,
Game Mania en TF-Robots).

Omdat elke shop een andere HTML-structuur heeft, gokken we niet blind op
CSS-classnamen van één specifiek platform. In plaats daarvan:

  1. Zoeken we eerst de kleinste elementen die zelf een prijs bevatten
     (bv. <bdi>€6,99</bdi>), en lopen we vanaf daar omhoog in de HTML-boom
     tot we een link + titel vinden. Dat werkt platform-onafhankelijk: elke
     webshop toont ergens compact een prijs, ongeacht de CSS-conventie.
  2. Als dat niets oplevert (bv. prijzen die met JavaScript worden
     ingeladen), vallen we terug op: elke link met genoeg tekst + een
     prijs-patroon in de buurt.

Dit is een best-effort aanpak. Sommige shops (vooral met zware
JavaScript-rendering) leveren misschien niets op — zie README.md voor hoe je
dat oplost.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.utils import get_session, polite_sleep, parse_price, clean_title, get_with_retry, add_page_param
import config


OUT_OF_STOCK_PHRASES = [
    "uitverkocht", "niet op voorraad", "geen voorraad", "sold out",
    "out of stock", "niet beschikbaar", "unavailable", "binnenkort",
    "pre-order", "preorder", "pre order", "nog niet leverbaar",
    "tijdelijk uitverkocht", "op=op", "notify me", "meld mij",
    "e-mail mij zodra", "email me when available", "back in stock",
    "wachtlijst", "waiting list", "in de wacht", "coming soon",
]

# Sommige shops tonen geen woord maar een expliciet aantal: "0 op voorraad",
# "voorraad: 0", "stock: 0".
ZERO_STOCK_RE = re.compile(r"\b(?:op\s*voorraad|voorraad|stock|available)\s*:?\s*0\b")


def _looks_out_of_stock(text: str) -> bool:
    low = text.lower()
    if any(phrase in low for phrase in OUT_OF_STOCK_PHRASES):
        return True
    return bool(ZERO_STOCK_RE.search(low))

PRICE_TAIL_RE = re.compile(r"€?\s?\d{1,4}[.,]\d{2}.*$")


def _dedupe_repeated(text: str) -> str:
    """'TitelTitel' -> 'Titel' (komt voor als image alt-text + zichtbare
    titel allebei in dezelfde link zitten, zoals bij Intertoys)."""
    n = len(text)
    if n > 4 and n % 2 == 0:
        half = n // 2
        if text[:half] == text[half:]:
            return text[:half]
    return text


def _clean_extracted_title(raw: str) -> str:
    title = PRICE_TAIL_RE.sub("", raw)
    title = clean_title(title)
    title = _dedupe_repeated(title)
    return title


def _price_leaf_elements(soup: BeautifulSoup, max_text_len: int = 40, max_descendants: int = 6):
    """Vind de meest-innerlijke elementen waarvan de eigen tekst een prijs is
    (bv. <bdi>&euro;6,99</bdi> of <span class="price">6,99</span>), zonder te
    hoeven gokken naar specifieke class-namen. Dit werkt platform-onafhankelijk:
    elke shop toont een prijs ergens compact bij elkaar, ongeacht de gebruikte
    CSS-conventie."""
    candidates = []
    for el in soup.find_all(True):
        text = el.get_text(" ", strip=True)
        if not text or len(text) > max_text_len:
            continue
        if parse_price(text) is None:
            continue
        if len(el.find_all(True)) > max_descendants:
            continue
        candidates.append(el)
    # Alleen de innerlijkste bewaren (geen candidate die een andere candidate omvat)
    innermost = [
        el for el in candidates
        if not any(el is not other and el in other.parents for other in candidates)
    ]
    return innermost


def _find_card_root(price_el, max_up: int = 9):
    """Loop vanaf een prijs-element omhoog in de boom tot we een voorouder
    vinden met een link + genoeg tekst — dat is vrijwel altijd de kaart/rij
    van 1 los product."""
    node = price_el
    for _ in range(max_up):
        if node.parent is None:
            break
        node = node.parent
        link = node.find("a", href=True)
        if not link:
            continue
        link_text = link.get_text(" ", strip=True)
        heading = node.find(["h1", "h2", "h3", "h4", "h5"])
        if len(link_text) > 3 or heading:
            return node, link
    return None, None


def _extract_via_product_classes(soup: BeautifulSoup, base_url: str) -> list[dict]:
    results = []
    seen = set()

    for price_el in _price_leaf_elements(soup):
        price_text = price_el.get_text(" ", strip=True)
        price = parse_price(price_text)
        if price is None:
            continue

        card, link = _find_card_root(price_el)
        if card is None:
            continue

        card_text = card.get_text(" ", strip=True)
        in_stock = not _looks_out_of_stock(card_text)

        title = ""
        heading = card.find(["h1", "h2", "h3", "h4", "h5"])
        if heading:
            title = _clean_extracted_title(heading.get_text(" ", strip=True))
        if not title:
            title = _clean_extracted_title(link.get_text(" ", strip=True))
        if len(title) < 4:
            continue

        url = urljoin(base_url, link["href"])
        key = (title.lower(), price)
        if key in seen:
            continue
        seen.add(key)
        results.append({"title": title, "price": price, "url": url, "in_stock": in_stock})

    return results


def _nearby_price(link, max_up: int = 4):
    """Zoek een prijs in de buurt van een link: eerst de link zelf, dan
    stapsgewijs omhoog — maar stop zodra een voorouder MEERDERE links bevat
    (dat betekent dat we de grens van 1 productkaart gepasseerd zijn en een
    prijs van een ander product zouden kunnen pakken)."""
    text = link.get_text(" ", strip=True)
    price = parse_price(text)
    if price is not None:
        return price, text
    node = link
    for _ in range(max_up):
        if node.parent is None:
            break
        node = node.parent
        distinct_hrefs = {a["href"] for a in node.find_all("a", href=True)}
        if len(distinct_hrefs) > 1:
            break
        node_text = node.get_text(" ", strip=True)
        price = parse_price(node_text)
        if price is not None:
            return price, node_text
    return None, text


def _extract_via_links_fallback(soup: BeautifulSoup, base_url: str) -> list[dict]:
    results = []
    seen = set()
    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        if len(text) < 6:
            continue
        price, context_text = _nearby_price(link)
        if price is None:
            continue
        in_stock = not _looks_out_of_stock(context_text)
        title = _clean_extracted_title(text)
        if len(title) < 4:
            continue
        url = urljoin(base_url, link["href"])
        key = (title.lower(), price)
        if key in seen:
            continue
        seen.add(key)
        results.append({"title": title, "price": price, "url": url, "in_stock": in_stock})
    return results


MAX_PAGES = 5  # de meeste shops hebben maar 1 pagina One Piece-producten; we
               # stoppen vanzelf zodra een pagina niks nieuws oplevert.
PAGINATION_MIN_RESULTS = 20  # onder dit aantal op pagina 1 proberen we geen pagina 2


def _fetch_page(session, url: str, shop_name: str):
    try:
        resp = get_with_retry(session, url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"  [!] {shop_name}: kon {url} niet ophalen ({e})")
        return None


def scrape(shop: dict) -> list[dict]:
    session = get_session()
    all_results = []

    for base_url in shop["urls"]:
        seen_urls_for_this_base = set()
        got_any_page = False

        for page in range(1, MAX_PAGES + 1):
            url = base_url if page == 1 else add_page_param(base_url, page)
            resp = _fetch_page(session, url, shop["name"])
            polite_sleep()
            if resp is None:
                break  # niet nog een keer proberen op nog hogere paginanummers

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "template"]):
                tag.decompose()

            page_results = _extract_via_product_classes(soup, url)
            if not page_results:
                page_results = _extract_via_links_fallback(soup, url)

            if not page_results:
                if page == 1:
                    print(f"  [!] {shop['name']}: geen producten gevonden op {url} "
                          f"— selector werkt hier niet, zie README 'Een shop repareren'")
                break

            # Nieuw t.o.v. wat we al hadden op eerdere pagina's van DEZE url?
            # Zo niet (bv. omdat de shop het ?page=N-patroon niet ondersteunt
            # en gewoon pagina 1 blijft teruggeven), stoppen we — verder
            # doorgaan zou alleen dubbele of onnodige requests opleveren.
            new_results = [r for r in page_results if r["url"] not in seen_urls_for_this_base]
            if not new_results:
                break

            for r in new_results:
                r["shop"] = shop["name"]
                seen_urls_for_this_base.add(r["url"])
            all_results.extend(new_results)
            got_any_page = True

            if len(new_results) < len(page_results) and page > 1:
                # gedeeltelijke overlap met de vorige pagina is ook een teken
                # dat we aan het einde van de echte resultaten zitten
                break

            # Pagina 1 met maar een handjevol producten wijst er vrijwel
            # altijd op dat dit alles is wat de shop heeft — dan is een 2e
            # pagina proberen alleen maar een onnodig extra verzoek (en
            # kan bij sommige shops zelfs bijdragen aan bot-detectie).
            if page == 1 and len(page_results) < PAGINATION_MIN_RESULTS:
                break

        if not got_any_page:
            continue

    return all_results

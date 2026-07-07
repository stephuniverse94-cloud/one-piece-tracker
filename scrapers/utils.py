"""Gedeelde hulpfuncties voor alle scrapers."""

import re
import time
import requests

import config


_session = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(
            {
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            }
        )
    return _session


# Statuscodes die het waard zijn om opnieuw te proberen — tijdelijke server-
# kant problemen. 403/404 juist NIET: dat is een blokkade of verkeerde URL,
# een 2e poging verandert daar niks aan en kost alleen maar tijd.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_with_retry(session: requests.Session, url: str, timeout: int,
                    max_retries: int = 2, backoff: float = 2.0) -> requests.Response:
    """Haalt een URL op met een paar nieuwe pogingen bij een tijdelijke hik
    (timeout, connectiefout, of een 429/5xx-status) — voorkomt dat een shop
    onterecht als 'kapot' geldt door 1 eenmalig netwerk-hikje."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code in _RETRYABLE_STATUS and attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
                continue
            return resp
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
                continue
    raise last_exc


def polite_sleep():
    time.sleep(config.REQUEST_DELAY)


def add_page_param(url: str, page: int) -> str:
    """Voegt een ?page=N (of &page=N) toe aan een URL, voor paginering."""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page={page}"


# Vindt prijzen in Europese notatie: "€ 6,99", "6,99", "€6.99", "94.99"
# We geven de voorkeur aan een leesteken gevolgd door precies 2 cijfers als
# decimaalscheiding (dat is vrijwel altijd de prijs, niet een setnummer of jaartal).
_PRICE_RE = re.compile(r"(?:€\s?)?(\d{1,4})[.,](\d{2})(?!\d)")


def parse_price(text: str) -> float | None:
    """Haal de eerste geldige prijs uit een stuk tekst. Retourneert None als
    er niets bruikbaars in staat."""
    if not text:
        return None
    match = _PRICE_RE.search(text)
    if not match:
        return None
    euros, cents = match.groups()
    try:
        return float(f"{euros}.{cents}")
    except ValueError:
        return None


def clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

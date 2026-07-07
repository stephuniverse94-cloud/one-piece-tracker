"""
Onthoudt alles wat het script tussen runs moet blijven weten:

- "alerted": welke deals al gemeld zijn (voorkomt herhaalde prijs-meldingen)
- "sold_out": welke shops al als "alles uitverkocht" gemeld zijn
- "stock": laatst bekende voorraadstatus per shop+set (voor restock-meldingen)
- "lowest_price": laagste ooit geziene prijs per set, ongeacht shop
- "failures": aantal opeenvolgende mislukte checks per shop

Regel voor prijs-meldingen: we melden opnieuw als
  (a) een shop+set-combinatie voor het eerst onder de grens zakt, of
  (b) de prijs verder gezakt is dan de vorige keer dat we 'm meldden.

Als een eerder gemelde deal weer boven de grens komt (of niet meer gevonden
wordt), verwijderen we 'm uit de state — zodat een nieuwe dip in de toekomst
gewoon weer een melding geeft.
"""

import json
import os
import config


def load_state() -> dict:
    defaults = {"alerted": {}, "sold_out": [], "stock": {}, "lowest_price": {}, "failures": {}}
    if not os.path.exists(config.STATE_FILE):
        return defaults
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, default_value in defaults.items():
                data.setdefault(key, default_value)
            return data
    except (json.JSONDecodeError, OSError):
        return defaults


def save_state(state: dict):
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def make_key(shop_id: str, category: str, code_or_vol: str) -> str:
    return f"{shop_id}|{category}|{code_or_vol}"


def should_alert(state: dict, key: str, price: float) -> bool:
    previous = state["alerted"].get(key)
    if previous is None:
        return True
    return price < previous - 0.001  # kleine marge tegen float-afrondingsgedoe


def record_alert(state: dict, key: str, price: float):
    state["alerted"][key] = price


def clear_stale(state: dict, still_active_keys: set):
    """Verwijder keys die deze run niet meer onder de grens zaten, zodat een
    volgende dip weer een melding triggert."""
    for key in list(state["alerted"].keys()):
        if key not in still_active_keys:
            del state["alerted"][key]


def newly_sold_out(state: dict, current_sold_out: list) -> list:
    """Geeft alleen de shops terug die NU voor het eerst 'alles uitverkocht'
    zijn — al bekende sold-out shops worden niet elke run opnieuw gemeld."""
    previously = set(state.get("sold_out", []))
    return [name for name in current_sold_out if name not in previously]


def update_sold_out(state: dict, current_sold_out: list):
    state["sold_out"] = current_sold_out


# ---------------------------------------------------------------------------
# Restock-meldingen (los van prijs)
# ---------------------------------------------------------------------------

def is_restock(state: dict, key: str, in_stock_now: bool) -> bool:
    """True als dit item de vorige keer expliciet uitverkocht was, en nu niet
    meer. Bij de EERSTE keer dat we een item zien (geen eerdere status bekend)
    melden we niks — dat is geen 'restock', gewoon de startsituatie."""
    previous = state["stock"].get(key)
    return previous is False and in_stock_now is True


def update_stock(state: dict, key: str, in_stock_now: bool):
    state["stock"][key] = in_stock_now


# ---------------------------------------------------------------------------
# Laagste prijs ooit gezien (per set, ongeacht welke shop)
# ---------------------------------------------------------------------------

def check_and_update_lowest(state: dict, price_key: str, price: float) -> bool:
    """Werkt het record bij en geeft True terug als dit een NIEUW laagterecord
    is (of de eerste keer dat we deze set zien)."""
    previous = state["lowest_price"].get(price_key)
    is_record = previous is None or price < previous - 0.001
    if previous is None or price < previous:
        state["lowest_price"][price_key] = price
    return is_record


# ---------------------------------------------------------------------------
# Shop lijkt al een tijdje stuk (opeenvolgende mislukte runs)
# ---------------------------------------------------------------------------

def record_shop_result(state: dict, shop_id: str, success: bool) -> int:
    """Werkt de teller bij en geeft de NIEUWE streak-waarde terug (0 bij
    succes). Bij succes wordt de teller gereset, zodat een shop die het na
    een storing weer doet niet 'stuk' blijft heten."""
    if success:
        state["failures"][shop_id] = 0
        return 0
    state["failures"][shop_id] = state["failures"].get(shop_id, 0) + 1
    return state["failures"][shop_id]


def is_persistent_failure(streak: int) -> bool:
    """We melden bij het bereiken van de drempel, en daarna elke keer dat de
    streak weer een veelvoud daarvan is (10, 20, 30, ...) — niet elke run,
    anders raakt de melding zinloos, maar ook niet nooit meer."""
    threshold = config.PERSISTENT_FAILURE_THRESHOLD
    return streak >= threshold and streak % threshold == 0

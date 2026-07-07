"""
Matcher: bepaalt of een gescrapete producttitel een Booster Pack, Booster Box
of Double Pack uit de watchlist is.

We matchen op de officiële set-CODE (OP-06, EB-02, Vol. 9, ...), niet op de
setnaam. Tijdens het onderzoek bleek dat een aantal shops andere namen
gebruiken dan in de watchlist staan (bv. OP-09 heet bij sommige shops
"Emperors in the New World" i.p.v. "Chosen by Fate"), maar de code zelf is
overal consistent.

Daarnaast bevat dit bestand is_english(): een taalfilter die Japanse/Franse/
Duitse/Koreaanse/Chinese kaarten uitsluit, ongeacht of ze goedkoper zijn dan
de Engelse variant.
"""

import re

# Woorden die aangeven dat het om een BOX/DISPLAY/CASE gaat i.p.v. een losse
# pack. Als een van deze in de titel staat, is het per definitie geen "Booster
# Pack" match (ook al staat de juiste OP-code er wel in).
BOX_KEYWORDS = [
    "box", "display", "case", "bundle", "sealed case",
    "boosterbox", "booster box", "boosterdisplay",
]

# Woorden die aangeven dat het om een Double Pack gaat. Let op: bewust GEEN
# "tin pack" hier — Tin Packs zijn een ander product (2 boosters + promo in
# een metalen blikje, eigen Vol.-nummering) en horen niet bij de Double Pack
# Sets uit je watchlist. Die sluiten we hieronder juist expliciet uit.
DOUBLE_PACK_KEYWORDS = [
    "double pack", "doublepack", "dp-", "dp0", "twin pack",
]

# Tin Packs bevatten vaak toevallig wel een OP-code in de titel ("Tin Pack Set
# Vol. 2 - Sabo OP-13"), maar zijn geen losse Booster Pack — sluiten we dus
# apart uit, zowel bij Booster Pack- als bij Booster Box-matching.
TIN_KEYWORDS = ["tin pack", "tin vol", "tin set"]


def is_tin_pack_listing(title: str) -> bool:
    t = _normalize(title)
    return any(kw in t for kw in TIN_KEYWORDS)


def _normalize(text: str) -> str:
    """Lowercase, en haal streepjes/spaties tussen letters en cijfers weg
    zodat 'OP-16', 'OP16' en 'OP 16' allemaal hetzelfde worden."""
    text = text.lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)  # unicode dashes -> gewone '-'
    return text


def _code_variants(code: str) -> list[str]:
    """Genereer schrijfwijzen van een code als 'OP-16': 'op-16', 'op16', 'op 16'."""
    base = code.lower()  # "op-16"
    no_dash = base.replace("-", "")  # "op16"
    spaced = base.replace("-", " ")  # "op 16"
    return [base, no_dash, spaced]


def is_box_or_display(title: str) -> bool:
    t = _normalize(title)
    return any(kw in t for kw in BOX_KEYWORDS)


def is_double_pack_listing(title: str) -> bool:
    t = _normalize(title)
    return any(kw in t for kw in DOUBLE_PACK_KEYWORDS)


# Voor het herkennen van een losse Booster BOX (24 packs, soms 20 bij Premium
# Boosters) gebruiken we een striktere set dan BOX_KEYWORDS hierboven — dat is
# expres breed ("case", "bundle", ...) om te voorkomen dat zulke dingen als
# losse pack worden gezien. Voor "dit IS een Booster Box" willen we het net
# andersom: specifiek genoeg om een Sealed Case (12 boxen, ~10x de prijs) of
# Booster Bundle/Tin (ander product) niet per ongeluk als Booster Box te tellen.
BOOSTER_BOX_KEYWORDS = ["booster box", "boosterbox", "booster display", "boosterdisplay"]
BOOSTER_BOX_EXCLUDE_KEYWORDS = TIN_KEYWORDS + [
    "sealed case", "case of", "per case", "bundle",
    "premium collection", "illustration",
]


def is_booster_box_listing(title: str) -> bool:
    t = _normalize(title)
    if is_double_pack_listing(title):
        return False
    if any(kw in t for kw in BOOSTER_BOX_EXCLUDE_KEYWORDS):
        return False
    return any(kw in t for kw in BOOSTER_BOX_KEYWORDS)


def match_booster_box(title: str, booster_packs: list[dict]) -> dict | None:
    """Geeft het watchlist-item terug als de titel een losse Booster Box is
    die matcht met een van de codes — of None."""
    if not is_booster_box_listing(title):
        return None
    t = _normalize(title)
    for item in booster_packs:
        if any(variant in t for variant in _code_variants(item["code"])):
            return item
    return None


# Losse kaarten (singles) hebben vaak toevallig een setcode in de titel
# ("One Piece OP06-119 Roronoa Zoro Parallel"), maar zijn geen sealed
# Booster Pack. We eisen daarom dat "booster" letterlijk in de titel staat —
# elke echte sealed booster die we tegenkwamen tijdens onderzoek had dat
# woord er wél in staan, singles vrijwel nooit.
def match_booster_pack(title: str, booster_packs: list[dict]) -> dict | None:
    """Geeft het watchlist-item terug als de titel een losse Booster Pack is
    die matcht met een van de codes — of None."""
    if is_box_or_display(title) or is_tin_pack_listing(title):
        return None
    t = _normalize(title)
    if "booster" not in t:
        return None
    for item in booster_packs:
        if any(variant in t for variant in _code_variants(item["code"])):
            return item
    return None


def double_pack_code_fallback(double_packs: list[dict], booster_packs: list[dict]) -> dict:
    """Bouwt Vol.N -> OP-code op basis van positie in de lijst (Vol.1..16
    staan in config.py in dezelfde volgorde/namen als OP-01..OP-16).

    Waarom dit nodig is: het 'Vol. N'-volgnummer is een apart, officieel
    Bandai-nummer dat NIET gelijk loopt met de OP-nummering (uit onderzoek
    bleek bv. dat het echte 'Vol. 9'-product de OP-14/EB-04 set bevat, niet
    OP-09). Maar sommige shops (o.a. Intertoys) labelen hun double packs
    juist wél met de OP-code i.p.v. een Vol.-nummer. Voor die shops gebruiken
    we de aanname uit je eigen watchlist (Vol.N hoort bij OP-0N) als
    fallback-signaal — dat is een bewuste keuze, geen garantie dat het
    exacte officiële Vol.-nummer overeenkomt. Zie README voor de details.

    Ook gebruikt door main.py om te bepalen of een Double Pack onder een
    PRIORITY_CODE valt (bv. OP-09).
    """
    mapping = {}
    for dp, bp in zip(double_packs, booster_packs):
        mapping[dp["vol"]] = bp["code"]
    return mapping


def match_double_pack(title: str, double_packs: list[dict], booster_packs: list[dict]) -> dict | None:
    """Geeft het watchlist-item terug als de titel een Double Pack is die
    matcht met een van de Vol.-nummers (of, als fallback, de bijbehorende
    OP/EB-code) — of None."""
    if is_box_or_display(title):
        return None
    if not is_double_pack_listing(title):
        return None
    t = _normalize(title)

    # Signaal 1: expliciet "Vol. N" of "DP-0N" in de titel — de betrouwbaarste match.
    for item in double_packs:
        vol = item["vol"]
        patterns = [rf"vol\.?\s*{vol}\b", rf"dp-?0?{vol}\b"]
        if any(re.search(p, t) for p in patterns):
            return item

    # Signaal 2 (fallback): geen Vol.-nummer gevonden, maar wel een OP/EB-code
    # die volgens jouw watchlist bij een Vol. hoort (zie docstring hierboven).
    code_fallback = double_pack_code_fallback(double_packs, booster_packs)
    for item in double_packs:
        code = code_fallback.get(item["vol"])
        if code and any(variant in t for variant in _code_variants(code)):
            return item

    return None


def classify_and_match(title: str, booster_packs: list[dict], double_packs: list[dict]):
    """Eén titel -> ('booster_pack' | 'booster_box' | 'double_pack' | None, watchlist_item | None)."""
    dp_match = match_double_pack(title, double_packs, booster_packs)
    if dp_match:
        return "double_pack", dp_match
    box_match = match_booster_box(title, booster_packs)
    if box_match:
        return "booster_box", box_match
    bp_match = match_booster_pack(title, booster_packs)
    if bp_match:
        return "booster_pack", bp_match
    return None, None


# ---------------------------------------------------------------------------
# TAALFILTER — alleen Engelstalige kaarten, geen Japans/Frans/Duits/Koreaans/
# Chinees. We blokkeren op signalen van een ANDERE taal i.p.v. te eisen dat
# "EN"/"ENG" letterlijk in de titel staat — bij de meeste shops is Engels
# namelijk de stille standaard (alleen de Japanse/andere import wordt expliciet
# gelabeld, precies omdat dat de uitzondering is). Simpelweg altijd "EN"
# vereisen zou dus juist een hoop legitiem-Engelse producten wegfilteren.
NON_ENGLISH_WORD_MARKERS = [
    "japans", "japanese", "japan",
    "frans", "french", "français", "francais",
    "duits", "german", "deutsch",
    "koreaans", "korean",
    "chinees", "chinese",
]

# "(JP)", "- JP", "24 FR", "(CN)" e.d. — we matchen deze 2-letter codes als los
# woord, ongeacht wat ervoor staat (spatie, streepje, haakje), want ze staan
# soms los aan het eind ("... Display 24 FR") en soms tussen haakjes. Bewust
# GEEN "DE"-variant hier: "de" is in het Nederlands gewoon het lidwoord "de"
# en zou te vaak per ongeluk matchen. Duits vangen we alleen via de volledige
# woorden hierboven (duits/german/deutsch).
NON_ENGLISH_TAG_RE = re.compile(r"\b(jp|fr|kr|cn)\b")


def is_english(title: str) -> bool:
    t = _normalize(title)
    if any(marker in t for marker in NON_ENGLISH_WORD_MARKERS):
        return False
    if NON_ENGLISH_TAG_RE.search(t):
        return False
    return True

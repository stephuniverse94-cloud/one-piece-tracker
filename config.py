"""
Config voor de One Piece TCG price tracker.

Alles wat je normaal gesproken wilt aanpassen (prijsgrenzen, shops aan/uit zetten,
sets toevoegen) staat in dit bestand — de rest van de code hoef je niet aan te raken.
"""

import os

# ---------------------------------------------------------------------------
# DISCORD
# ---------------------------------------------------------------------------
# Zet je webhook-URL NIET hier hardcoded — die komt uit een environment variable
# (lokaal via .env, op GitHub via Settings > Secrets > Actions > DISCORD_WEBHOOK_URL)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# WATCHLIST — rechtstreeks overgenomen uit je PDF
# ---------------------------------------------------------------------------
# "code" is wat we gebruiken om te matchen met productteksten op de shops
# (OP-06, EB-02, ...). "name" is puur voor leesbaarheid in de Discord-melding.
# We matchen op CODE, niet op naam — sommige shops gebruiken net iets andere
# namen voor dezelfde set (bv. OP-09 heet bij sommige shops "Emperors in the
# New World" i.p.v. "Chosen by Fate" zoals in je watchlist). De code (OP-09)
# is overal hetzelfde, dus dat is de betrouwbare match.

BOOSTER_PACK_ALERT_PRICE = 10.00

# Sets die als eerste getoond worden in de Discord-melding, los van welke shop
# de deal heeft. Verandert niets aan hóe er gescraped wordt (we lezen nog
# steeds de hele shoppagina in één keer in, zie README), maar bepaalt de
# volgorde in de melding en in de terminal-output.
PRIORITY_CODES = ["OP-09", "EB-03"]

BOOSTER_PACKS = [
    {"code": "OP-01", "name": "Romance Dawn"},
    {"code": "OP-02", "name": "Paramount War"},
    {"code": "OP-03", "name": "Pillars of Strength"},
    {"code": "OP-04", "name": "Kingdoms of Intrigue"},
    {"code": "OP-05", "name": "Awakening of the New Era"},
    {"code": "OP-06", "name": "Siege of Justice"},
    {"code": "OP-07", "name": "500 Years in the Future"},
    {"code": "OP-08", "name": "Two Legends"},
    {"code": "OP-09", "name": "Chosen by Fate"},
    {"code": "OP-10", "name": "Royal Blood"},
    {"code": "OP-11", "name": "The Time of Battle"},
    {"code": "OP-12", "name": "Legacy of the Master"},
    {"code": "OP-13", "name": "The Future"},
    {"code": "OP-14", "name": "The Azure Seas"},
    {"code": "OP-15", "name": "Adventure on Kami's Island"},
    {"code": "OP-16", "name": "The Time of Battle"},
    {"code": "EB-01", "name": "Memories of the Legends"},
    {"code": "EB-02", "name": "Side Stories"},
    {"code": "EB-03", "name": "Heroines Edition"},
    # Nog niet (allemaal) uitgekomen op moment van schrijven — alvast klaarzetten
    # zodat je niks hoeft te doen zodra een shop 'm gaat voeren. Matching gaat
    # op de CODE, dus de naam hieronder doet er functioneel niet toe; pas 'm
    # aan zodra Bandai de officiële naam bekendmaakt.
    {"code": "OP-17", "name": "The World's Strongest Warriors"},  # 4th Anniversary Booster, al in pre-order bij enkele shops
    {"code": "OP-18", "name": "(nog aan te kondigen)"},
    {"code": "OP-19", "name": "(nog aan te kondigen)"},
    {"code": "OP-20", "name": "(nog aan te kondigen)"},
]

DOUBLE_PACK_ALERT_PRICE = 16.00

# Losse Booster Boxes (24 packs, soms 20 bij Premium Boosters) — dezelfde 19
# sets als BOOSTER_PACKS hierboven, alleen de doos i.p.v. 1 los pack.
BOOSTER_BOX_ALERT_PRICE = 150.00

# Extra veiligheidsnet: als een match een compleet onrealistische prijs heeft
# voor dat producttype, is het vermoedelijk een verkeerde match (bv. een losse
# kaart die per ongeluk toch als booster pack matcht) i.p.v. een echte deal.
# Zo'n uitschieter wordt genegeerd i.p.v. gemeld — met een waarschuwing in de
# log, zodat je het wel kan zien als het vaker gebeurt.
PRICE_SANITY_RANGES = {
    "booster_pack": (3.00, 15.00),
    "booster_box": (50.00, 300.00),
    "double_pack": (8.00, 30.00),
}

# Let op: het "Vol. N" nummer bij Double Packs is een apart, officieel Bandai
# volgnummer — dat loopt NIET gelijk met de OP-nummering (Vol. 9 hoort bv. niet
# per se bij OP-09). We matchen daarom puur op "Vol. N" / "DP-0N" tekst, niet
# op de setnaam.
DOUBLE_PACKS = [
    {"vol": 1, "name": "Romance Dawn"},
    {"vol": 2, "name": "Paramount War"},
    {"vol": 3, "name": "Pillars of Strength"},
    {"vol": 4, "name": "Kingdoms of Intrigue"},
    {"vol": 5, "name": "Awakening of the New Era"},
    {"vol": 6, "name": "Siege of Justice"},
    {"vol": 7, "name": "500 Years in the Future"},
    {"vol": 8, "name": "Two Legends"},
    {"vol": 9, "name": "Chosen by Fate"},
    {"vol": 10, "name": "Royal Blood"},
    {"vol": 11, "name": "The Time of Battle"},
    {"vol": 12, "name": "Legacy of the Master"},
    {"vol": 13, "name": "The Future"},
    {"vol": 14, "name": "The Azure Seas"},
    {"vol": 15, "name": "Adventure on Kami's Island"},
    {"vol": 16, "name": "The Time of Battle"},
]

# ---------------------------------------------------------------------------
# SHOPS
# ---------------------------------------------------------------------------
# platform "shopify"      -> we gebruiken de /products.json trick (betrouwbaar,
#                             geen HTML-scraping nodig)
# platform "html"         -> generieke HTML-scraper met een paar fallback-
#                             strategieën (zie scrapers/generic.py)
#
# "enabled": False zet een shop tijdelijk uit zonder 'm te verwijderen.
# Bol.com zit er expres niet bij — dat regel jij via hun affiliate API.

SHOPS = [
    # --- Nederland ---------------------------------------------------------
    {
        "id": "intertoys",
        "name": "Intertoys",
        "country": "NL",
        "platform": "html",
        "urls": ["https://www.intertoys.nl/one-piece-tcg"],
        "product_url_prefix": "https://www.intertoys.nl",
        "enabled": True,
    },
    {
        "id": "dracoon",
        "name": "Dracoon",
        "country": "NL",
        "platform": "html",
        "urls": [
            "https://dracoon.nl/trading-cards/one-piece-card-game/one-piece-card-game-boosterpacks/",
            "https://dracoon.nl/trading-cards/one-piece-card-game/one-piece-card-game-boosterboxen/",
        ],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "catchyourcards",
        "name": "Catch Your Cards",
        "country": "NL",
        "platform": "html",
        "urls": [
            "https://catchyourcards.nl/onepiece/boosterbox/",
            "https://catchyourcards.nl/onepiece/double-pack/",
            "https://catchyourcards.nl/onepiece/",
        ],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "pocketgames",
        "name": "PocketGames",
        "country": "NL",
        "platform": "shopify",
        "urls": ["https://pocketgames.nl/collections/one-piece"],
        "enabled": True,
    },
    {
        "id": "spellenvariant",
        "name": "Spellenvariant",
        "country": "NL",
        "platform": "html",
        "urls": ["https://www.spellenvariant.nl/trading-card-games/one-piece-card-game"],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "rarecards",
        "name": "RareCards",
        "country": "NL",
        "platform": "shopify",
        "urls": ["https://rarecards.nl/en/collections/one-piece-tcg"],
        "enabled": True,
    },
    {
        "id": "optcg",
        "name": "OPTCG",
        "country": "NL",
        "platform": "shopify",
        "urls": ["https://optcg.nl/collections/one-piece-tcg"],
        "enabled": True,
    },
    {
        "id": "tf-robots",
        "name": "TF-Robots",
        "country": "NL",
        "platform": "html",
        "urls": ["https://www.tf-robots.nl/c-7113482/one-piece-tcg/"],
        "product_url_prefix": "https://www.tf-robots.nl",
        "enabled": True,
    },
    {
        "id": "speelkaartenwinkel",
        "name": "Speelkaartenwinkel",
        "country": "NL",
        "platform": "html",
        "urls": ["https://www.speelkaartenwinkel.nl/trading-cards/onepiece.html"],
        "product_url_prefix": "",
        "enabled": True,
    },
    # --- België --------------------------------------------------------------
    {
        "id": "gamemania",
        "name": "Game Mania",
        "country": "BE",
        "platform": "html",
        "urls": ["https://www.gamemania.be/nl/info/boardgames-en-tcg/one-piece"],
        "product_url_prefix": "https://www.gamemania.be",
        "enabled": True,
    },
    {
        "id": "outpostbrussels",
        "name": "Outpost Brussels",
        "country": "BE",
        "platform": "shopify",
        "urls": ["https://outpostbrussels.be/en/collections/one-piece-1"],
        "enabled": True,
    },
    {
        "id": "gamelootz",
        "name": "GameLootz",
        "country": "BE",
        "platform": "html",
        "urls": ["https://www.gamelootz.be/en/one-piece-trade-card-game"],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "aition",
        "name": "Aition",
        "country": "BE",
        "platform": "html",
        "urls": [
            "https://www.aition.be/one-piece-card-game",
            "https://www.aition.be/one-piece-booster-boxes",
        ],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "cardgameshop",
        "name": "Cardgameshop",
        "country": "BE",
        "platform": "html",
        "urls": ["https://www.cardgameshop.be/en/categories/one-piece"],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "tcgstore",
        "name": "Trading Card Game Store",
        "country": "BE",
        "platform": "html",
        # Geen aparte categoriepagina bevestigd tijdens onderzoek — gok op
        # basis van hun site-structuur, controleer en pas aan indien nodig.
        "urls": ["https://tradingcardgamestore.com/product-categorie/one-piece/"],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "vinticards",
        "name": "Vinticards",
        "country": "BE",
        "platform": "html",
        "urls": ["https://vinticards.be/product-categorie/one-piece/"],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "maximus",
        "name": "Maximus",
        "country": "BE",
        "platform": "html",
        "urls": ["https://maximus.be/product-categorie/one-piece/"],
        "product_url_prefix": "",
        "enabled": True,
    },
    {
        "id": "tspelgeweld",
        "name": "Tspelgeweld",
        "country": "BE",
        "platform": "html",
        "urls": ["https://www.tspelgeweld.be/nl/product/list/one-piece-tcg/38026"],
        "product_url_prefix": "https://www.tspelgeweld.be",
        "enabled": True,
    },
    {
        "id": "startspeler",
        "name": "Startspeler",
        "country": "BE",
        "platform": "html",
        "urls": ["https://startspeler.com/trading-card-games/one-piece.html"],
        "product_url_prefix": "",
        "enabled": True,
    },
    # --- Overig (niet specifiek 1 land, verzenden naar NL+BE) --------------
    {
        "id": "tcg-ground",
        "name": "TCG Ground",
        "country": "BE",
        "platform": "html",
        "urls": ["https://www.tcg-ground.com/one_piece/4"],
        "product_url_prefix": "https://www.tcg-ground.com",
        "enabled": True,
    },
    {
        "id": "tcgreus",
        "name": "TcgReus",
        "country": "NL",
        "platform": "shopify",
        "urls": [
            "https://www.tcgreus.nl/en/collections/one-piece-booster-packs",
            "https://www.tcgreus.nl/en/collections/one-piece-booster-boxen",
        ],
        "enabled": True,
    },
    {
        "id": "premiumcardsupply",
        "name": "PremiumCardSupply",
        "country": "NL",
        "platform": "shopify",
        # Geen aparte "one piece"-collectie kunnen bevestigen tijdens onderzoek,
        # dus pakken we alle producten — de matcher filtert vanzelf op OP/EB-codes.
        "urls": ["https://premiumcardsupply.nl/collections/all"],
        "enabled": True,
    },
]

# ---------------------------------------------------------------------------
# OVERIG
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 15  # seconden per HTTP-verzoek
REQUEST_DELAY = 1.5   # seconden pauze tussen requests naar dezelfde shop (beleefd blijven)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

STATE_FILE = "state.json"  # onthoudt welke deals al gemeld zijn, zie state.py

# Na hoeveel opeenvolgende mislukte runs (elke 30 min) we een aparte "shop
# lijkt al een tijdje stuk"-melding sturen. 10 runs = ~5 uur.
PERSISTENT_FAILURE_THRESHOLD = 10

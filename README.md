# One Piece TCG Price Tracker

Checkt elke 30 minuten de prijzen van One Piece Booster Packs (< €10),
Booster Boxes (< €150) en Double Packs (< €16) bij 22 NL/BE webshops, en
stuurt een Discord-melding zodra iets onder de grens zakt. OP-09 en EB-03
krijgen voorrang in de melding. Je krijgt nooit een link naar iets dat
uitverkocht is — en als een shop voor je hele watchlist niks op voorraad
heeft, krijg je daar 1x een aparte melding van. Bol.com zit er expres niet
bij — dat regel je apart via hun affiliate API (zie onderaan).

## Hoe het werkt

- **4 shops draaien op Shopify** (PocketGames, RareCards, OPTCG, Outpost
  Brussels) — daarvoor gebruiken we hun `/products.json`-endpoint. Geen
  scraping, gewoon nette data. Zeer betrouwbaar.
- **De overige 15 shops** worden gescraped: we halen de HTML van de
  One Piece-categoriepagina op en zoeken naar productblokken + prijzen.
- We matchen op de **officiële set-code** (OP-06, EB-02, Vol. 9, ...), niet
  op de setnaam — een paar shops gebruiken net andere namen voor dezelfde
  set dan in je watchlist staan, maar de code is overal hetzelfde.
- **Alleen Engelstalige kaarten.** Titels met een Japanse/Franse/Duitse/
  Koreaanse/Chinese taalmarkering (bv. "(JP)", "- FR", "Japanse Booster",
  "(Japanese)") worden genegeerd, ook als die net iets goedkoper zijn dan de
  Engelse versie. Bij ontbreken van een taalmarkering gaan we uit van Engels
  — dat is bij vrijwel alle shops de stille standaard; alleen de Japanse/
  andere import wordt meestal expliciet gelabeld. Zie `is_english()` in
  `matcher.py` als je dit strenger of losser wil maken.
- **Booster Boxes tellen ook mee** (< €150), naast losse Booster Packs en
  Double Packs. We herkennen specifiek "Booster Box"/"Booster Display" —
  Sealed Cases (12 boxen ineens), Booster Bundles en Tin Packs worden bewust
  NIET als Booster Box gezien, dat zijn andere producten met een heel andere
  prijs. Zie `BOOSTER_BOX_KEYWORDS` in `matcher.py`.
- **OP-09 en EB-03 hebben voorrang** (`config.PRIORITY_CODES`): als daar een
  deal voor gevonden wordt, komt die als éérste Discord-bericht binnen, apart
  van de rest. Dit verandert niks aan hóe er gescraped wordt (we lezen nog
  steeds de hele shop-pagina in 1x in, zie hieronder) — alleen de volgorde
  van de melding. Voeg zelf codes toe/verwijder ze in `config.py`.
- **Nooit een link naar iets uitverkochts.** Zowel de Shopify-shops (via hun
  eigen voorraad-veld, 100% betrouwbaar) als de overige shops (via
  tekst-herkenning van "uitverkocht"/"sold out"/"tijdelijk uitverkocht"/etc.)
  worden gecheckt op voorraad. Uitverkochte producten tellen niet mee als
  deal, ook al is de prijs op dat moment wel laag genoeg.
- **"Alles uitverkocht"-melding**: als we bij een shop wél producten van je
  watchlist vinden, maar er ECHT geen enkele op voorraad is (i.p.v. gewoon te
  duur), krijg je daar een aparte, korte Discord-melding van. Dat gebeurt
  maar 1x zolang de situatie zo blijft — je krijgt 'm dus niet elke 30
  minuten opnieuw. Zodra er weer iets op voorraad komt (of weer helemaal
  uitverkocht raakt na een periode van wél voorraad), kan de melding opnieuw
  verschijnen.
- **Nieuwe shops** (naast de oorspronkelijke 19): **TCG Ground**, **TcgReus**
  (Shopify — booster packs én boxen als aparte collecties) en
  **PremiumCardSupply** (Shopify). Startspeler stond er al in.
- **OP-17 t/m OP-20 staan al klaar** in de watchlist, ook al zijn niet alle
  vier al uitgekomen. Zodra een shop ze gaat voeren, wordt dat gewoon
  meegenomen — je hoeft dan niks aan te passen. Namen die nog "(nog aan te
  kondigen)" zijn, mag je zelf bijwerken in `config.py` zodra Bandai ze
  aankondigt (functioneel maakt de naam niks uit, we matchen op code).
- **Restock-meldingen, los van prijs.** Naast de prijs-alerts krijg je ook een
  melding zodra een set weer op voorraad komt bij een shop waar 'ie eerder
  uitverkocht was — ongeacht of de prijs onder je grens zit. Handig voor
  schaarse sets die soms gewoon nergens te krijgen zijn. Wordt niet gemeld bij
  de eerste keer dat we een item zien (dat is geen "restock", gewoon de
  startsituatie), en niet nogmaals zolang het op voorraad blijft.
- **"Laagste ooit gezien"-markering** (🏆) bij een deal die het laagste
  bedrag is dat we ooit voor die set geregistreerd hebben, over alle shops
  heen. Puur informatief, verandert niks aan óf je een melding krijgt.
- **`python main.py --status`**: toont de huidige prijs bij elke shop voor je
  hele watchlist, los van prijsgrenzen en voorraad — handig om gewoon even
  rond te kijken. Stuurt nooit iets naar Discord en raakt de state niet aan.
- **Detectie van langdurig kapotte shops**: als een shop 10 checks op rij
  (~5 uur) faalt, krijg je een aparte melding — dat wijst eerder op een
  kapotte URL/selector dan een tijdelijk hikje. Komt daarna nog terug bij 20,
  30, etc. mislukkingen, niet elke keer opnieuw.
- **Automatisch opnieuw proberen** bij een tijdelijk netwerk-hikje (timeout,
  connectiefout, of een 429/5xx-serverfout) — tot 2 extra pogingen met een
  oplopende pauze ertussen. Een 403/404 wordt NIET opnieuw geprobeerd, want
  dat is een blokkade of verkeerde URL, geen tijdelijk probleem — een 2e
  poging verandert daar toch niks aan.
- **Prijs-sanity-check**: een match met een compleet onrealistische prijs
  voor dat producttype (bv. een "Booster Pack" van €0,50 of €500) wordt
  genegeerd i.p.v. gemeld — dat is vermoedelijk een verkeerde match, geen
  echte deal. Verschijnt wel als waarschuwing in de log, zodat je het ziet
  als het vaker gebeurt. Bereiken staan in `config.PRICE_SANITY_RANGES`.
- **Paginering**: shops met meer dan 1 pagina One Piece-producten worden nu
  tot 5 pagina's diep gecheckt (via `?page=2`, `?page=3`, ...), en stoppen
  vanzelf zodra een pagina niks nieuws meer oplevert — dus geen onnodige
  extra requests bij shops die maar 1 pagina hebben.
- Elke shop+set-combinatie wordt maar 1x gemeld zolang de prijs niet verder
  zakt (zie `state.json`) — anders krijg je elke 30 minuten dezelfde melding
  zolang een deal blijft staan.

## Setup

### 1. Discord webhook aanmaken

Server-instellingen → Integraties → Webhooks → Nieuwe webhook → kopieer de URL.

### 2. Repo op GitHub zetten

```bash
cd one-piece-tracker
git init && git add . && git commit -m "Initial version"
git remote add origin https://github.com/<jouw-username>/one-piece-tracker.git
git push -u origin main
```

**Belangrijk:** maak de repo **public**. GitHub Actions geeft private repos
maar 2000 gratis minuten/maand — bij elke 30 minuten checken zit je daar met
19 shops overheen. Public repos krijgen onbeperkte gratis Actions-minuten.
Er staan geen wachtwoorden in de code (de webhook-URL komt uit een Secret),
dus public zetten is geen probleem.

### 3. Secret instellen

Repo → Settings → Secrets and variables → Actions → New repository secret
→ naam `DISCORD_WEBHOOK_URL`, waarde = je webhook-URL.

Dat is het. De workflow in `.github/workflows/check_prices.yml` draait nu
automatisch elke 30 minuten. Je kan 'm ook meteen handmatig starten via de
"Actions"-tab → "Check One Piece TCG prices" → "Run workflow".

## Lokaal testen

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

python main.py --dry-run              # alle shops, print resultaten, stuurt niks
python main.py --shop dracoon --dry-run   # test 1 shop
python main.py --status               # huidige prijzen tonen, los van prijsgrenzen
python main.py                         # echte run
```

## Een shop repareren

Bij 15 van de 19 shops moet de generieke scraper de HTML-structuur "raden"
(zie `scrapers/generic.py`) — die probeert eerst elementen met "product" in
de class-naam, en anders elke link met een prijs erbij. Dat werkt bij de
meeste shops, maar niet gegarandeerd bij allemaal, vooral shops die producten
met JavaScript laden in plaats van kant-en-klare HTML.

Als een shop niks oplevert (je ziet dat in de terminal-output als
`geen producten gevonden`):

1. Open de URL uit `config.py` gewoon in je browser, rechtermuisknop →
   "Pagina bron bekijken" (niet "Element inspecteren" — dat toont de
   JS-aangepaste versie, we willen de originele HTML die `requests` ook
   krijgt).
2. Zoek naar de class-naam rond een productprijs (Ctrl+F op een prijs die je
   op de pagina ziet staan).
3. Stuur me die class-naam / een stukje HTML en ik pas `generic.py` aan met
   een specifieke selector voor die shop — of voeg 'm zelf toe als
   `if shop["id"] == "spellenvariant": ...` uitzondering in
   `_extract_via_product_classes`.

Twee shops (Spellenvariant en Trading Card Game Store) hebben in `config.py`
een **gegokte** categorie-URL staan, omdat ik tijdens het onderzoek geen
directe bevestiging kon vinden van hun exacte "alle One Piece producten"
overzichtspagina. Check die twee als eerste als er ergens 0 producten
gevonden worden.

### "403 Forbidden" bij een shop

Sommige shops (in de eerste test: Catch Your Cards, Game Mania) blokkeren het
verzoek met een 403-foutmelding. Dat is vrijwel altijd bot-detectie
(Cloudflare of vergelijkbaar) — en die systemen blokkeren vaak specifiek
bekende cloud-datacenter IP-reeksen, wat GitHub Actions nu eenmaal is. Met
andere woorden: dit werkt soms wél als je het script lokaal op je eigen PC
draait (thuis-IP), maar niet vanuit GitHub Actions. Als een shop hardnekkig
403 blijft geven ondanks nette browser-headers, is scrapen daar helaas geen
haalbare weg zonder een zwaardere aanpak (bv. een headless browser via een
externe dienst) — je kan die shop dan het beste op `"enabled": False` zetten.

## Bol.com toevoegen (via de affiliate API)

Zodra je een affiliate-account + API-key hebt via developers.bol.com, kun je
een `scrapers/bol.py` toevoegen die de Catalog API aanroept in plaats van
HTML te scrapen — net als de Shopify-aanpak, maar dan met OAuth2. Laat het
weten als je daar hulp bij wil, dan bouwen we die erbij zodra je de
credentials hebt.

## Aanpassen

Alles wat je normaal wil wijzigen staat in `config.py`:

- `BOOSTER_PACK_ALERT_PRICE` / `BOOSTER_BOX_ALERT_PRICE` / `DOUBLE_PACK_ALERT_PRICE` — de prijsgrenzen
- `PRIORITY_CODES` — welke sets bovenaan de melding komen
- `PERSISTENT_FAILURE_THRESHOLD` — na hoeveel mislukte checks op rij je een
  "shop lijkt stuk"-melding krijgt (standaard 10 = ~5 uur)
- `SHOPS` — zet `"enabled": False` om een shop tijdelijk te pauzeren
- `BOOSTER_PACKS` / `DOUBLE_PACKS` — nieuwe sets toevoegen zodra Bandai ze
  aankondigt (geldt automatisch ook voor Booster Box-tracking, die hergebruikt
  dezelfde lijst)

Check-interval aanpassen (bv. naar elk uur): pas de `cron`-regel aan in
`.github/workflows/check_prices.yml` ("*/30 * * * *" → "0 * * * *").

## Beperkingen

- Paginering stopt automatisch bij 5 pagina's (`MAX_PAGES` in
  `scrapers/generic.py` / `scrapers/shopify.py`). Voor een niche-categorie
  als One Piece zou dat ruim genoeg moeten zijn, maar als een shop toch meer
  heeft, kun je dat getal verhogen.
- We checken alleen shops die de HTML direct meesturen. Een enkele shop kan
  in de toekomst overstappen op volledig JavaScript-gerenderde content — dan
  werkt de generieke scraper niet meer en is een aparte aanpak nodig
  (bv. met een headless browser).

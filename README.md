# scubaduikers

scubaduikers - de start van je duik

## tech setup

door middel van FastAPI en Sqlite (litestream voor streaming backups) een basic setup die de workload voorlopig aan moet kunnen. SQLModel voor database setup aangezien verwachting is dat het minimaal zal zijn. 

## doelen

- registreren informatie duiklocaties (nederland) en gebruikers mogelijkheid bieden om wijzigingen in te schieten
- als duikvereniging de mogelijkheid hebben om (verenigings)duiken te organiseren en aanmeldingen bij te houden
- een open platform om duiken te organiseren zonder account gatekeeping

Duiken is qua totale aantal leden bij NOB een niche sport met veelal do it yourself oplossingen die het goed draaien van een vereniging bemoeilijken. Ook zie je dat huidige oplossingen zwaar op Meta leunen in de vorm van Whatsapp en Facebook waar ook niet iedereen deel van wil worden. 

Ook het eenvoudiger over duikverenigingen heen samen duiken zou op termijn moeten kunnen. Nu moet iedereen altijd in tig Whatsapp/Facebook groepen gaan zitten zonder eenduidig overzicht. 

Verder is er nog geen community based website waarbij informatie over duikstekken bijgehouden kan worden. Dit zou bij genoeg massa qua gebruikers voor meer en correctere informatie moeten zorgen. Dit stimuleert de duiksport in Nederland.

## tech

Lokaal testen

```bash
uv run fastapi dev main.py
```

Prod data lokaal halen om te testen

```bash
python restore_prod_db.py
python restore_prod_db.py --confirm
```

## docs

uv & fastapi [docs](https://docs.astral.sh/uv/guides/integration/fastapi/)
litestream [dcos](https://litestream.io/guides/kubernetes/)
fastapi [reference](https://fastapi.tiangolo.com/reference/)

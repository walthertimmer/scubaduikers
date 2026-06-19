# scubaduikers

[scubaduikers](https://scubaduikers.nl) - de start van je duik

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

Testdata invoeren

```bash
python ./tests/seed_test_data.py
```

Superadmin instellen

```bash
sqlite3 /data/scubaduikers.db \
  "UPDATE user SET is_superadmin = 1 WHERE email = 'your-email@example.com';"
```

of met python aangezien the containers de sqlite3 CLI niet bevatten

```python
kubectl exec -n scubaduikers scubaduikers-xx-yy -c scubaduikers -- \
  python3 -c "import sqlite3; conn = sqlite3.connect('/data/scubaduikers.db'); conn.execute(\"UPDATE user SET is_superadmin = 1 WHERE email = 'user@mail.com'\"); conn.commit(); conn.close()"
```

## docs

uv & fastapi [docs](https://docs.astral.sh/uv/guides/integration/fastapi/)  
litestream [dcos](https://litestream.io/guides/kubernetes/)  
fastapi [reference](https://fastapi.tiangolo.com/reference/)  

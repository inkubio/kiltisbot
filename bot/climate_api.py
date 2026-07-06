import config  # Optionally define the API_KEY here
from db_utils import save_climate_data  # Or make your own function to save to a database
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiosqlite
import pathlib
import aiohttp_cors


BASE_DIR = pathlib.Path(__file__).parent.parent
DB_PATH = BASE_DIR / "climate.db"

async def get_climate_data(request):
    HEL = ZoneInfo("Europe/Helsinki")
    UTC = ZoneInfo("UTC")

    # 1. Luetaan parametrit (voivat olla None)
    start_str = request.rel_url.query.get('start')
    end_str = request.rel_url.query.get('end')

    # Otetaan "nyt" talteen heti, jotta se on johdonmukainen
    now_hel = datetime.now(HEL)

    try:
        # --- LOGIIKKA PUUTTUVILE ARVOILLE ---

        # TAPAUS A: Käyttäjä ei antanut kumpaakaan -> Viimeiset 24h
        if not start_str and not end_str:
            end_dt_hel = now_hel
            start_dt_hel = now_hel - timedelta(hours=24)

        # TAPAUS B: Käyttäjä antoi vain ALUN -> Alusta tähän hetkeen
        elif start_str and not end_str:
            start_dt_hel = datetime.fromisoformat(start_str).replace(tzinfo=HEL)
            end_dt_hel = now_hel

        # TAPAUS C: Käyttäjä antoi vain LOPUN -> Lopusta 24h taaksepäin
        elif not start_str and end_str:
            end_dt_hel = datetime.fromisoformat(end_str).replace(tzinfo=HEL)
            start_dt_hel = end_dt_hel - timedelta(hours=24)

        # TAPAUS D: Molemmat annettu -> Käytetään niitä
        else:
            start_dt_hel = datetime.fromisoformat(start_str).replace(tzinfo=HEL)
            end_dt_hel = datetime.fromisoformat(end_str).replace(tzinfo=HEL)

    except ValueError:
        return web.json_response(
            {"error": "Virheellinen päivämäärä.", "example": "2026-01-18T12:00"},
            status=400
        )

    # --- TARKISTUKSET ---
    if start_dt_hel > end_dt_hel:
        return web.json_response({"error": "Alkuaika ei voi olla loppuajan jälkeen."}, status=400)

    # --- MUUNNOS JA HAKU ---
    start_utc = start_dt_hel.astimezone(UTC)
    end_utc = end_dt_hel.astimezone(UTC)

    # --- HAKU KANNASTA ---
    try:
        # Kutsutaan äsken tehtyä funktiota
        db_rows = await fetch_measurements_from_db(start_utc, end_utc)

        # --- MUUNNOS SUOMEN AIKAAN ---
        response_data = []
        for row in db_rows:
            # 1. Kerrotaan Pythonille, että kannasta tullut aika on UTC
            # (Oletus: kantaan on tallennettu ilman aikavyöhykettä, eli "naive")
            row_time_utc = datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC)

            # 2. Käännetään Suomen aikaan
            row_time_hel = row_time_utc.astimezone(HEL)

            response_data.append({
                "timestamp": row_time_hel.isoformat(),
                "temperature": row["temp"],
                "humidity": row["humi"],
                "co2": row["co2"]
            })

        # Palautetaan oikea data
        return web.json_response({
            "meta": {
                "count": len(response_data),
                "start_requested": start_dt_hel.isoformat(),
                "end_requested": end_dt_hel.isoformat(),
            },
            "data": response_data
        }, status=200)

    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)
    # Kun vastaat käyttäjälle, palauta JSON:
    return web.json_response({
        "meta": {
            "start": start_dt_hel.isoformat(),
            "end": end_dt_hel.isoformat(),
            "timezone": "Europe/Helsinki"
        },
        "data": [ ... ] # Mittaustulokset tähän
    })

async def fetch_measurements_from_db(start_dt, end_dt):
    """
    Hakee mittaukset annetulta aikaväliltä.
    start_dt ja end_dt tulevat tänne valmiiksi UTC-muodossa.
    """
    # Muutetaan datetime-objektit stringeiksi, koska SQLite vertailee niitä tekstinä
    # Oletus: kannassa ajat ovat muodossa "2026-01-18 10:00:00"
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT timestamp, temperature, humidity, co2
        FROM climate_data
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Palauttaa tulokset sanakirjana (helpompi käsitellä)
            db.row_factory = aiosqlite.Row

            async with db.execute(query, (start_str, end_str)) as cursor:
                rows = await cursor.fetchall()

                # Muutetaan aiosqlite-rivit tavalliseksi listaksi
                results = []
                for row in rows:
                    results.append({
                        "created_at": row["timestamp"],  # Nimi kannassa
                        "temp": row["temperature"],
                        "humi": row["humidity"],
                        "co2": row["co2"]
                    })
                return results

    except Exception as e:
        print(f"Tietokantavirhe: {DB_PATH} - {e}")
        return [] # Palautetaan tyhjä lista virhetilanteessa

async def upload_sensor(request):
    """
    Creates a connection to the raspberry pi which is collecting data to a database.
    Handles formatting and checking wheter there is data to save.
    """
    auth_header = request.headers.get('Authorization')
    if auth_header != f"Bearer {config.API_KEY}":
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except ConnectionResetError:
        print("Varoitus: Raspberry Pi katkaisi yhteyden kesken lähetyksen (Timeout?)")
        return web.json_response({"error": "Connection lost during transfer"}, status=408)
    except Exception as e:
        print(f"Muu virhe datan luvussa: {e}")
        return web.json_response({"error": "Data transfer failed"}, status=500)
    
    temp = data.get('temperature')
    humidity = data.get('humidity')
    co2 = data.get('co2')

    if temp is None or humidity is None or co2 is None:
        return web.json_response({"error": "Missing temperature, humidity, or CO2"}, status=400)

    try:
        temp = float(temp)
        humidity = float(humidity)
        co2 = float(co2)
    except ValueError:
        return web.json_response({"error": "Invalid numeric values"}, status=400)

    save_climate_data(co2, temp, humidity)  # HUOM: päivitä myös tämä funktio!
    print(f"Sensor data received: Temp={temp}, Humidity={humidity}, CO2={co2}")
    return web.json_response({"status": "Sensor data received"})

async def index(request):
    return web.FileResponse('./index.html')

def create_web_app():
    app = web.Application()

    # 1. Rekisteröidään reitit
    app.add_routes([
        web.get('/', index),
        web.post('/upload_sensor', upload_sensor), # Raspberry
        web.get('/ilmanlaatu', get_climate_data)   # Julkinen API
    ])

    # 2. CORS-asetukset (Sallitaan nettisivujen hakea dataa)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    # Lisätään CORS-säännöt kaikkiin reitteihin
    for route in list(app.router.routes()):
        cors.add(route)

    return app

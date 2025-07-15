from aiohttp import web
import json
import config  # Optionally define the API_KEY here
from db_utils import save_climate_data  # Or make your own function to save to a database


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


def create_web_app():
    """
    Create a web app, through which the climate data is handled.
    """
    app = web.Application()
    app.add_routes([web.post('/upload_sensor', upload_sensor)])
    return app

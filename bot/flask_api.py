import os
from flask import Flask, request, jsonify
from datetime import datetime
from utils import save_image, get_latest_image_path, image_is_recent, analyze_coffee
import config


app = Flask(__name__)


@app.route('/upload_sensor', methods=['POST'])
def upload_sensor():
    """
    Endpoint, johon Raspberry Pi ilmanlaatumittari lähettää mittaustietoa JSON-formaatissa.
    """
    token = request.headers.get('Authorization')
    if token != f"Bearer {API_KEY}":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No JSON data"}), 400

    temp = data.get('temperature')
    humidity = data.get('humidity')
    if temp is None or humidity is None:
        return jsonify({"error": "Missing temperature or humidity data"}), 400

    try:
        temp = float(temp)
        humidity = float(humidity)
    except ValueError:
        return jsonify({"error": "Invalid temperature or humidity value"}), 400

    # Tallennus tietokantaan
    save_climate_data(temp, humidity)

    print(f"Sensor data received: Temp={temp}, Humidity={humidity}")

    return jsonify({"status": "Sensori data vastaanotettu."})


if __name__ == '__main__':
    # Flask kuuntelee kaikilla IP-osoitteilla portissa 8000
    app.run(host='0.0.0.0', port=8000)

import os
from flask import Flask, request, jsonify
from datetime import datetime
from utils import save_image, get_latest_image_path, image_is_recent, analyze_coffee

last_analysis = {"timestamp": None, "result": None}

app = Flask(__name__)

# Haetaan API avain
API_KEY = os.getenv("API_KEY")

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

    # Tallennus tietokantaan tai tiedostoon voisi tapahtua tässä.
    print(f"Sensor data received: {data}")

    return jsonify({"status": "Sensori data vastaanotettu."})


if __name__ == '__main__':
    # Flask kuuntelee kaikilla IP-osoitteilla portissa 8000
    app.run(host='0.0.0.0', port=8000)

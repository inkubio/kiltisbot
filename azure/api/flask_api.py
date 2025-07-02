import os
from flask import Flask, request, jsonify
from datetime import datetime
from utils import save_image, get_latest_image_path, image_is_recent

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

@app.route("/get_latest_analysis", methods=["POST"])
def get_latest_analysis():

    token = request.headers.get('Authorization')
    if token != f"Bearer {API_KEY}":
        return jsonify({"error": "Unauthorized"}), 401

    now = datetime.now()
    timestamp = last_analysis["timestamp"]
    age_ok = timestamp and now - timestamp < timedelta(minutes=5)

    if not age_ok:
        try:
            # Pyydä kuva raspberrylta
            resp = requests.post("http://raspberry.local:8000/get_image")
            if resp.status_code != 200:
                raise Exception("Raspberry image request failed")

            image_bytes = io.BytesIO(resp.content)
            image = Image.open(image_bytes)

            # Tee analyysi
            result = "2 cups" #analyze_coffee(image)
            last_analysis["timestamp"] = now
            last_analysis["result"] = result

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({
        "timestamp": last_analysis["timestamp"].isoformat(),
        "result": last_analysis["result"]
    })

if __name__ == '__main__':
    # Flask kuuntelee kaikilla IP-osoitteilla portissa 8000
    app.run(host='0.0.0.0', port=8000)

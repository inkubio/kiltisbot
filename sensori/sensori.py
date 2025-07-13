import time
import requests
import random

API_KEY = "your_api_key_here"  # same as config.API_KEY on server
SERVER_URL = "http://<server-ip>:8000/upload_sensor"  # change to real IP


def get_fake_sensor_data():
    """
    Replace this with real sensror readings if available.
    """
    return {
        "temperature": round(random.uniform(20.0, 25.0), 2),
        "humidity": round(random.uniform(30.0, 50.0), 2),
        "co2": round(random.uniform(400.0, 700.0), 2)
    }


def send_data():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    while True:
        sensor_data = get_fake_sensor_data()
        try:
            response = requests.post(SERVER_URL, json=sensor_data, headers=headers, timeout=5)
            print(f"[{time.ctime()}] Sent data: {sensor_data} | Status: {response.status_code}")
        except Exception as e:
            print(f"[{time.ctime()}] Failed to send data: {e}")

        time.sleep(180)  # every 3 minutes


if __name__ == "__main__":
    send_data()

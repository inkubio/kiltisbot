import requests
import time
from picamera import PiCamera
import io

API_URL = "http://<AZURE_VM_IP>:5000/upload_image"
API_KEY = "your_api_key_here"

def capture_and_send():
    camera = PiCamera()
    camera.resolution = (640, 480)  # Matalaresoluutio

    stream = io.BytesIO()
    camera.capture(stream, format='jpeg')
    stream.seek(0)

    headers = {"Authorization": f"Bearer {API_KEY}"}
    files = {'image': ('image.jpg', stream, 'image/jpeg')}

    try:
        response = requests.post(API_URL, headers=headers, files=files)
        print(f"Response from server: {response.json()}")
    except Exception as e:
        print(f"Error sending image: {e}")

if __name__ == '__main__':
    while True:
        capture_and_send()
        time.sleep(60)  # Kuva joka minuutti
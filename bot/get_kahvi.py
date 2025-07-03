import os
from datetime import datetime, timedelta
import base64

IMAGE_FILENAME = "last.jpg"

# Save base64 image
def save_image(image_b64, directory):
    img_data = base64.b64decode(image_b64)
    filepath = os.path.join(directory, IMAGE_FILENAME)
    with open(filepath, 'wb') as f:
        f.write(img_data)

# Get full path of the latest image
def get_latest_image_path(directory):
    return os.path.join(directory, IMAGE_FILENAME)

# Check if image is recent (within N minutes)
def image_is_recent(directory, minutes=5):
    filepath = get_latest_image_path(directory)
    if not os.path.exists(filepath):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    return datetime.now() - mtime < timedelta(minutes=minutes)

def analyze_coffee(image):
    gray = image.convert("L")  # Muutetaan harmaasävykuvaksi
    pixels = list(gray.getdata())
    threshold = 50  # mikä on tumma pikseli
    dark_pixels = sum(1 for p in pixels if p < threshold)
    return f"{dark_pixels}"

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
            resp = requests.post("http://localhost:6000")
            if resp.status_code != 200:
                raise Exception("Raspberry image request failed")

            image_bytes = io.BytesIO(resp.content)
            image = Image.open(image_bytes)

            # Tee analyysi
            result = result = analyze_coffee(image)
            last_analysis["timestamp"] = now
            last_analysis["result"] = result

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({
        "timestamp": last_analysis["timestamp"].isoformat(),
        "result": last_analysis["result"]
    })
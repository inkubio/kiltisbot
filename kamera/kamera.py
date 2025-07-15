from flask import Flask, send_file
from io import BytesIO
import subprocess


# Requires a POST tunnel  ssh -i azure -N -R 6000:localhost:7000 azureuser@40.127.166.0


def take_photo():
    filename = "/home/oskar/photo.jpg"
    cmd = ["raspistill", "-o", filename, "-t", "5", "-n"]
    subprocess.run(cmd, check=True)

    with open(filename, "rb") as f:
        img_bytes = f.read()

    return img_bytes


app = Flask(__name__)


@app.route('/', methods=['POST'])
def send_image():
    print("POST-pyyntö vastaanotettu")

    img_bytes = take_photo()

    return send_file(
        BytesIO(img_bytes),
        mimetype="image/jpeg",
        as_attachment=False,
        download_name="photo.jpg"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()  # Lataa .env-tiedoston muuttujat

kiltistoken = os.getenv("KILTIS_TOKEN")
CLIENT_ID_kilta = os.getenv("CLIENT_ID_KILTA")
CLIENT_SECRET_kilta = os.getenv("CLIENT_SECRET_KILTA")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SP_USERNAME_kilta = os.getenv("SP_USERNAME_KILTA")
FLASK_URL = os.getenv("FLASK_URL")
API_KEY = os.getenv("API_KEY")


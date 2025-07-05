import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()  # Lataa .env-tiedoston muuttujat

kiltistoken = os.getenv("KILTIS_TOKEN")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SP_USERNAME_kilta = os.getenv("SP_USERNAME_KILTA")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
FLASK_URL = os.getenv("FLASK_URL")
API_KEY = os.getenv("API_KEY")
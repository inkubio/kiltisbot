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

quotedb = "quote.db"
init_quote_db = "CREATE TABLE IF NOT EXISTS quotes (quote_text TEXT, tags TEXT, message_id INT, chat_id INT, said_by TEXT, added_by TEXT, said_date TEXT, added_date TEXT)"
jokedb = "joke.db"
init_joke_db = "CREATE TABLE IF NOT EXISTS jokes (joke_text TEXT, tags TEXT, date_added INT)"
climatedb = "climate.db"
init_climate_db = "CREATE TABLE IF NOT EXISTS climate_data (id INTEGER PRIMARY KEY AUTOINCREMENT, co2 REAL, temperature REAL, humidity REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"


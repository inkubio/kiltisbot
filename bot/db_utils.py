import sqlite3

def _init_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    return conn, c

quotedb = "quote.db"
init_quote_db = "CREATE TABLE IF NOT EXISTS quotes (quote_text TEXT, tags TEXT, message_id INT, chat_id INT, said_by TEXT, added_by TEXT, said_date TEXT, added_date TEXT)"
jokedb = "joke.db"
init_joke_db = "CREATE TABLE IF NOT EXISTS jokes (joke_text TEXT, tags TEXT, date_added INT)"
climatedb = "climate.db"
init_climate_db = "CREATE TABLE IF NOT EXISTS climate_data (id INTEGER PRIMARY KEY AUTOINCREMENT, co2 REAL, temperature REAL, humidity REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"

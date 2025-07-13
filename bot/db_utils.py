import sqlite3


def _init_db(path):
    """
    Create a connection to a desired database
    """
    conn = sqlite3.connect(path)
    c = conn.cursor()
    return conn, c


#  Databaseinformation for creating them
quotedb = "quote.db"
init_quote_db = "CREATE TABLE IF NOT EXISTS quotes (quote_text TEXT, tags TEXT, message_id INT, chat_id INT, said_by TEXT, added_by TEXT, said_date TEXT, added_date TEXT)"
jokedb = "joke.db"
init_joke_db = "CREATE TABLE IF NOT EXISTS jokes (joke_text TEXT, tags TEXT, date_added INT)"
climatedb = "climate.db"
init_climate_db = "CREATE TABLE IF NOT EXISTS climate_data (id INTEGER PRIMARY KEY AUTOINCREMENT, co2 REAL, temperature REAL, humidity REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"
songdb = "song.db"
init_song_db = "CREATE TABLE IF NOT EXISTS songs (song_name TEXT, song_melody TEXT, song_writers TEXT, song_composers TEXT, song_number TEXT, page_number TEXT, song_lyrics TEXT)"


def save_climate_data(co2, temperature, humidity):
    """
    Passively saving climate data from the guildroom through a raspberry pi into a database.
    """
    conn, c = _init_db(climatedb)
    try:
        c.execute("INSERT INTO climate_data (co2, temperature, humidity) VALUES (?, ?, ?)",
                  (co2, temperature, humidity))
        conn.commit()
    except Exception as e:
        print("Failed to save climate data:", e)
    finally:
        conn.close()

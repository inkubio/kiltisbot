"""
This bot is a new iteration on the old Kiltisbot made for Inkubio ry.
Heavily inspired by the old bot but with updated functionality.

Uptated by:
Aaro Kuusinen & Oskari Niemi
TG: @apeoskari / @oskarikalervo
email: kuusinen.aaro@gmail.com / okkixi@gmail.com
"""

import logging
import sqlite3
from typing import List
import requests
import os
import random
import spotipy
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from spotipy.oauth2 import SpotifyOAuth
import time
import json
from aiohttp import web
from multiprocessing import Process

import config
from db_utils import _init_db, quotedb, init_quote_db, jokedb, init_joke_db, climatedb, init_climate_db
import coffee
from joke import get_joke, add_joke
from quote import list_quotes, add_quote, delete_quote, get_quote
from climate import guild_data, get_plot, people_count
from logger import logger
from climate_api import create_web_app
from trivia import trivia

LOCAL_TZ = ZoneInfo("Europe/Helsinki")

def _init_db(database):
    """
        Initializes database connection
        Returns cursor to interact with db
        """
    connection = sqlite3.connect(database)
    return connection, connection.cursor()


def _create_db(database, init_query):
    print("Initializing database...")
    conn = sqlite3.connect(database)
    c = conn.cursor()
    try:
        c.executescript(init_query)
        conn.commit()
        conn.close()
        print("Success.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        conn.close()
        quit()
    else:
        conn.close()



"""
Define command a few command handlers and how they are used.
These will define the actual functionality of the bot and can be used by the user. 
Commands also in quote.py, joke.py, coffee.py and climate.py
"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns a help message with instructions on how to use the bot.
    Should be get up to date with the functionalities of the bot.
    """
    await update.message.reply_text("Commands:\n\n"
                                    "/help ->\nThis message\n\n"
                                    "/coffee ->\nGet a picture of the coffee pot at the guildroom.\n\n"
                                    "/events ->\nGet future guild events.\n\n"
                                    "/music ->\nWhat music is currently playing at the guildroom.\n\n"
                                    "/plot ->\nDraw a plot from the climate data (last 24h)\n"
                                    "CO2: Solid line every 200ppm and dashed every 100ppm\n"
                                    "Temperature: Solid line every degree and dashed every half a degree\n"
                                    "Humidity: Solid line every 5% and dashed every 2,5%\n\n"
                                    "/numbers ->\nGet most recent climate data from the guildroom "
                                    "& estimated people count (same as with /stalk)\n\n"
                                    "/stalk ->\nGet an estimated latest occupancy of the guildroom (RIP kiltiscam :()."
                                    " Based on the climate data gathered "
                                    "(currently a simple linear model based on co2 levels)\n\n"
                                    "/addquote ->\nAdd a quote to the bot by replying to a message.\n"
                                    "Example: /addquote exampltag1\n"
                                    "(Tags are necessary only with voice messages, "
                                    "but also help finding quotes later)\n\n"
                                    "/fact ->\nGet a random useless fact.\n\n"
                                    "/trivia ->\nGet a random trivia quiz.\n\n"
                                    "/quote -> \nGet a quote from the bot. Random if no added a search argument like "
                                    "the quotee, text in quote or tags.\n"
                                    "Example: /quote funny\n\n"
                                    "/listquotes ->\nGet a list of quotes from the bot\n"
                                    "(Works only in private chat with the bot)\n\n"
                                    "/deletequote ->\nDelete a quote from the bot by adding the quite ID. "
                                    "Get the ID with /listquotes.\n"
                                    "(Works only in private chat with the bot)\n\n"
                                    "/addjoke ->\nAdd a joke to the bot by replying to one or by writing one as an "
                                    "argument after the command.\n\n"
                                    "/joke ->\nGet a joke from the bot based on search arguments. Otherwise random.\n\n"
                                    "If there are any problems with the bot or suggestions for future functions,"
                                    "contact spagutmk or @apeoskari")


async def music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Luo auth_manager ilman cachea (tai käytä vain refresh_tokenia)
        auth_manager = SpotifyOAuth(
            client_id=config.SPOTIPY_CLIENT_ID,
            client_secret=config.SPOTIPY_CLIENT_SECRET,
            redirect_uri=config.REDIRECT_URI,
            scope="user-read-currently-playing",
            cache_path=None  # Estetään turha .cache-tiedosto
        )

        # 🔁 Päivitä access token käyttäen refresh tokenia
        token_info = auth_manager.refresh_access_token(config.REFRESH_TOKEN)
        access_token = token_info.get("access_token")

        if not access_token:
            await update.message.reply_text("❌ Failed to retrieve access token.")
            return

        # 🎵 Hae tiedot nykyisestä kappaleesta
        spotify = spotipy.Spotify(auth=access_token)
        track = spotify.current_user_playing_track()

        if track and track.get("item"):
            name = track["item"].get("name", "Unknown title")
            artist = track["item"]["artists"][0].get("name", "Unknown artist")
            await update.message.reply_text(f'🎶 Now playing:\n"{name}"\nby {artist}')
        else:
            await update.message.reply_text("🛑 Nothing is currently playing.")

    except Exception as e:
        print(f"Error in music(): {e}")
        await update.message.reply_text("⚠️ Error retrieving playback status.")

async def fun_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
        response.raise_for_status()
        data = response.json()
        fact = data.get("text", "Couldn't find a fact right now.")
    except Exception as e:
        fact = f"Error fetching fact: {e}"
    
    await update.message.reply_text(fact)

def parse_event_time(timestr):
    """Parses ISO time string with or without timezone."""
    if 'T' in timestr:
        # Time specified, likely with UTC offset
        return datetime.fromisoformat(timestr).astimezone(LOCAL_TZ)
    else:
        # All-day event, date only
        return datetime.fromisoformat(timestr).replace(tzinfo=LOCAL_TZ)

def format_event(event):
    start_raw = event['start'].get('dateTime', event['start'].get('date'))
    end_raw = event['end'].get('dateTime', event['end'].get('date'))

    start_dt = parse_event_time(start_raw)
    end_dt = parse_event_time(end_raw)
    same_day = start_dt.date() == end_dt.date()

    today = datetime.now(LOCAL_TZ).date()
    tomorrow = today + timedelta(days=1)

    if start_dt.date() == today:
        day_label = "Today"
    elif start_dt.date() == tomorrow:
        day_label = "Tomorrow"
    else:
        day_label = start_dt.strftime('%a, %b, %d')

    if 'dateTime' in event['start']:
        # Timed event
        time_str = (f"{day_label} {start_dt.strftime('%H:%M')} - "
                    f"{end_dt.strftime('%H:%M') if same_day else end_dt.strftime('%a, %b %d %H:%M')}")
    else:
        # All-day event
        if same_day:
            time_str = f"{day_label} (all day)"
        else:
            time_str = f"{day_label} - {end_dt.strftime('%a, %b %d')} (all day)"

    summary = event.get('summary', 'No title')
    
    location = event.get('location', '')
    location_text = ""
    if location:
        location_text = f"\n📍 {html.escape(location)}"

    return f"📅 <b>{summary}</b>\n🕒 {time_str}{location_text}".strip()

async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://www.googleapis.com/calendar/v3/calendars/{config.CALENDAR_ID}/events"
    now = datetime.utcnow().isoformat() + 'Z'
    params = {
        'key': config.GOOGLE_CALENDAR_API_KEY,
        'timeMin': now,
        'maxResults': 5,
        'orderBy': 'startTime',
        'singleEvents': 'true'
    }

    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        items = resp.json().get("items", [])

        if not items:
            await update.message.reply_text("No upcoming events found.")
            return

        event_texts = [format_event(item) for item in items]
        message = "\n\n".join(event_texts)
        await update.message.reply_text(message, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to fetch events: {e}")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Error handling and logging.
    """
    logger.warning('Update "%s" caused error "%s"' % (update, error))


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Printing updates for debugging.
    """
    print(update)


def start_bot():

    # Create databases if they don't already exist
    if not os.path.isfile(quotedb):
        _create_db(quotedb, init_quote_db)
    if not os.path.isfile(jokedb):
        _create_db(jokedb, init_joke_db)
    if not os.path.isfile(climatedb):
        _create_db(climatedb, init_climate_db)

    # Create the Application and pass it your bot's token (found int the config-file)
    application = Application.builder().token(config.kiltistoken).build()

    # On different commands, answer in Telegram accordingly.
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("coffee", coffee.get_coffee))
    application.add_handler(CommandHandler("events", events))
    application.add_handler(CommandHandler("music", music))
    application.add_handler(CommandHandler("plot", get_plot))
    application.add_handler(CommandHandler("numbers", guild_data))
    application.add_handler(CommandHandler("stalk", people_count))
    application.add_handler(CommandHandler("fact", fun_fact))
    application.add_handler(CommandHandler("trivia", trivia))
    application.add_handler(CommandHandler("addquote", add_quote))
    application.add_handler(CommandHandler("quote", get_quote))
    application.add_handler(CommandHandler("listquotes", list_quotes))
    application.add_handler(CommandHandler("deletequote", delete_quote))
    application.add_handler(CommandHandler("addjoke", add_joke))
    application.add_handler(CommandHandler("joke", get_joke))
    

    # For debugging
    # application.add_handler(CommandHandler("echo", echo))

    # Add an error handler.
    application.add_error_handler(error)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def run_web_app():
    app = create_web_app()
    web.run_app(app, host='0.0.0.0', port=8000)

def main() -> None:
    bot_process = Process(target=start_bot)
    bot_process.start()
    print(f"Bot process started with PID {bot_process.pid}")
    
    run_web_app()
    
    bot_process.join()  # Odottaa botin loppumista (Ctrl-C)


if __name__ == '__main__':
    main()

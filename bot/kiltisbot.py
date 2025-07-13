"""
This bot is a new iteration on the old Kiltisbot made for Inkubio ry.
Heavily inspired by the old bot but with updated functionality.
Thanks to Joonas Palosuo for the old code <3 !!!

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
import spotipy
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from spotipy.oauth2 import SpotifyOAuth
from aiohttp import web
from multiprocessing import Process

import config
from db_utils import quotedb, init_quote_db, jokedb, init_joke_db, climatedb, init_climate_db, songdb, init_song_db
import coffee
from joke import get_joke, add_joke
from quote import list_quotes, add_quote, delete_quote, get_quote
from climate import guild_data, get_plot, people_count
from logger import logger
from climate_api import create_web_app
from trivia import trivia
from virpi import get_song, add_song, delete_song

LOCAL_TZ = ZoneInfo("Europe/Helsinki")


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
Define a few command handlers and how they are used.
These will define the actual functionality of the bot and can be used by the user. 
Commands also in quote.py, joke.py, coffee.py, climate.py, plot.py, trivia.py and virpi.py
"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns a help message with instructions on how to use the bot.
    Should be get up to date with the functionalities of the bot.
    """
    await update.message.reply_text("<u><b>Commands & Instructions:</b></u>\n\n"
                                    ""
                                    "/help ->\n"
                                    "This message.\n\n"
                                    ""
                                    "/coffee ->\n"
                                    "Get a picture of the coffee pot at the guildroom.\n\n"
                                    ""
                                    "/events ->\n"
                                    "Get future guild events.\n\n"
                                    ""
                                    "/music ->\n"
                                    "What music is currently playing at the guildroom.\n\n"
                                    ""
                                    "/virpi ->\n"
                                    "Search for a song from the latest VIRPI based on the name or lyrics.\n"
                                    "If no exact match found, the best search results are shown.\n"
                                    "Then try again."
                                    "<b>Example:</b> /virpi hyvät ystävät"
                                    ""
                                    "/plot ->\n"
                                    "Draws a plot from the climate data <i>(last 24h)</i>\n"
                                    "<b>CO2:</b> Solid line every 200ppm and dashed every 100ppm\n"
                                    "<b>Temp:</b> Solid line every 1°C and dashed every 0,5°C\n"
                                    "<b>Humid:</b> Solid line every 5% and dashed every 2,5%\n\n"
                                    ""
                                    "/numbers ->\n"
                                    "Get most recent climate data from the guildroom "
                                    "& estimated people count <i>(same as with /stalk)</i>\n\n"
                                    ""
                                    "/stalk ->\n"
                                    "Get an estimated latest occupancy of the guildroom (RIP kiltiscam :(). "
                                    "Based on the climate data\n"
                                    "<i>(Currently a simple linear model based on co2 levels)</i>\n\n"
                                    ""
                                    "/fact ->\n"
                                    "Get a random useless fact.\n\n"
                                    ""
                                    "/trivia ->\n"
                                    "Get a random trivia quiz.\n\n"
                                    ""
                                    "/addquote ->\n"
                                    "Add a quote to the bot by replying to a message.\n"
                                    "<b>Example:</b> /addquote exampltag1\n"
                                    "<i>(Tags are necessary only with voice messages, "
                                    "but also help finding other quotes later)</i>\n"
                                    "<b>❌⚠️IMPORTANT!⚠️❌\n"
                                    "Quotes are chat specific!</b>\n\n"
                                    ""
                                    "/quote -> \n"
                                    "Get a quote from the bot. Random if no added a search argument like "
                                    "the quotee, text in quote or tags.\n"
                                    "<b>Example:</b> /quote funny\n\n"
                                    ""
                                    "/listquotes ->\n"
                                    "Get a list of your own quotes from the bot\n"
                                    "<i><u>(Works only in private chat with the bot)</u></i>\n\n"
                                    ""
                                    "/deletequote ->\n"
                                    "Delete your quote from the bot by adding the quite ID.\n"
                                    "Get the ID with /listquotes.\n"
                                    "<b>Example:</b> /deletequote 1234"
                                    "<i><u>(Works only in private chat with the bot\n"
                                    "and you can delete only your own quotes)</u></i>\n\n"
                                    ""
                                    "/addjoke ->\n"
                                    "Add a joke to the bot by replying to one or by writing one as an "
                                    "argument after the command.\n"
                                    "<b>❌⚠️IMPORTANT!⚠️❌\n"
                                    "Jokes are global and NOT chat specific!</b>\n\n"
                                    ""
                                    "/joke ->\n"
                                    "Get a joke from the bot based on search arguments. Otherwise random.\n\n"
                                    ""
                                    "If there are any problems with the bot or suggestions for future functions,"
                                    "contact spagutmk or @apeoskari/@oskarikalervo",
                                    parse_mode="HTML")


async def music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Fetches the current song playing on the guild spotify-account.
    AKA what's playing in the guildroom
    """
    try:
        # Create auth_manager without cache (or use just refresh_token)
        auth_manager = SpotifyOAuth(
            client_id=config.SPOTIPY_CLIENT_ID,
            client_secret=config.SPOTIPY_CLIENT_SECRET,
            redirect_uri=config.REDIRECT_URI,
            scope="user-read-currently-playing",
            cache_path=None  # Preventing an unnecessary .cache-file
        )

        # 🔁 Update access token using refresh token
        token_info = auth_manager.refresh_access_token(config.REFRESH_TOKEN)
        access_token = token_info.get("access_token")

        if not access_token:
            await update.message.reply_text("❌ Failed to retrieve access token.")
            return

        # 🎵 Retreive information about the current song
        spotify = spotipy.Spotify(auth=access_token)
        track = spotify.current_user_playing_track()

        if track and track.get("item"):
            name = track["item"].get("name", "Unknown title")
            artist = track["item"]["artists"][0].get("name", "Unknown artist")
            await update.message.reply_text(f'🎶 Now playing:\n'
                                            f'<b>"{name}"</b>\n'
                                            f'by <i>{artist}</i>',
                                            parse_mode="HTML")
        else:
            await update.message.reply_text("🛑 Nothing is currently playing.")

    except Exception as e:
        print(f"Error in music(): {e}")
        await update.message.reply_text("⚠️ Error retrieving playback status.")


async def fun_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Retrieves a fun/useless fact from an api for them.
    Can also be changed to other facts.
    """
    try:
        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
        response.raise_for_status()
        data = response.json()
        fact = data.get("text", "Couldn't find a fact right now.")
    except Exception as e:
        fact = f"Error fetching fact: {e}"
    
    await update.message.reply_text(fact)


def parse_event_time(timestr):
    """
    Parses ISO time string with or without timezone.
    """
    if 'T' in timestr:
        # Time specified, likely with UTC offset
        return datetime.fromisoformat(timestr).astimezone(LOCAL_TZ)
    else:
        # All-day event, date only
        return datetime.fromisoformat(timestr).replace(tzinfo=LOCAL_TZ)


def format_event(event):
    """
    Formats event information into a desired string format.
    """
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
        day_label = start_dt.strftime('%a, %b %d')

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

    return f"📅 <b>{summary}</b>\n🕒 <b>{time_str}</b><i>{location_text}</i>".strip()


async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends a formatted list of up to 5 upcoming guildevents to a chat.
    """
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
    if not os.path.isfile(songdb):
        _create_db(songdb, init_song_db)

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
    application.add_handler(CommandHandler("virpi", get_song))
    application.add_handler(CommandHandler("addsong", add_song))        # Hidden from other users
    application.add_handler(CommandHandler("deletesong", delete_song))  # Hidden from other users

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

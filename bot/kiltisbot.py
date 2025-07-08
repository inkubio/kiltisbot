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
                                    "/music ->\nWhat music is currently playing at the guildroom\n\n"
                                    "/stalk ->\nGet an estimated current occupancy of the guildroom. RIP kiltiscam :(\n\n"
                                    "/numbers ->\nGet climate data from the guildroom & estimated people count\n\n"
                                    "/plot ->\nDraws plots from the guildroom atmospheric data (last 24h)\n\n"
                                    "/addquote ->\nAdd a quote to the bot\n\n"
                                    "/quote -> \nGet a quote from the bot\n\n"
                                    "/listquotes ->\nGet a list of quotes from the bot\n\n"
                                    "/deletequote ->\nDelete a quote from the bot\n\n"
                                    "/joke ->\nGet a joke from the bot\n\n"
                                    "/addjoke ->\nAdd a joke to the bot\n\n"
                                    "/coffee ->\nHow much coffee is in quildroom coffee pan\n\n"
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
    application.add_handler(CommandHandler("music", music))
    application.add_handler(CommandHandler("stalk", people_count))
    application.add_handler(CommandHandler("numbers", guild_data))
    application.add_handler(CommandHandler("plot", get_plot))
    application.add_handler(CommandHandler("addquote", add_quote))
    application.add_handler(CommandHandler("quote", get_quote))
    application.add_handler(CommandHandler("listquotes", list_quotes))
    application.add_handler(CommandHandler("deletequote", delete_quote))
    application.add_handler(CommandHandler("joke", get_joke))
    application.add_handler(CommandHandler("addjoke", add_joke))
    application.add_handler(CommandHandler("coffee", coffee.get_coffee))

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

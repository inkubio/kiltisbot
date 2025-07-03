"""
This bot is a new iteration on the old Kiltisbot made for Inkubio ry.
Heavily inspired by the old bot but with updated functionality.

Questions or suggestions to
Aaro Kuusinen
TG: @apeoskari
email: kuusinen.aaro@gmail.com

Coffee related questions to:
Oskari Niemi
TG: @oskarikalervo
email: okkixi@gmail.com
"""

import logging
import sqlite3
from typing import List

import config
import spotipy
import plot_data
import coffee_analysis
import requests
import os


from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from spotipy.oauth2 import SpotifyOAuth
import time
import socket


# Enable logging.
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# Set a higher logging level for httpx to avoid all GET and POST requests being logged.
logging.getLogger("httpx").setLevel(logging.WARNING)
# noinspection DuplicatedCode
logger = logging.getLogger(__name__)


def _init_db(database):
    """
        Initializes database connection
        Returns cursor to interact with db
        """
    connection = sqlite3.connect(database)
    return connection, connection.cursor()


def _create_db(database, init_query):
    print("Initializing database...")
    conn, c = _init_db(database)
    try:
        c.execute(init_query)
        conn.commit()
        conn.close()
        print("Success.")
    finally:
        print("Failed to initialize database!")
        conn.close()
        quit()


def _get_message_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    return " ".join([tag for tag in string.split() if tag[0] != '/'])


"""
Define command a few command handlers and how they are used.
These will define the actual functionality of the bot and can be used by the user.
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
                                    "If there are any problems with the bot or suggestions for future functions,"
                                    "contact spagutmk or @apeoskari")


async def music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Connect to the Spotify's API to get access to the guild's account data.
    Then return the current song playing at the guildroom
    or a message telling that nothing is currently playing.
    """
    try:
        scope = "user-read-currently-playing"
        spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=config.CLIENT_ID_kilta,
                                                            client_secret=config.CLIENT_SECRET_kilta,
                                                            redirect_uri=config.REDIRECT_URI,
                                                            scope=scope,
                                                            username=config.SP_USERNAME_kilta))
        track = spotify.current_user_playing_track()
        await update.message.reply_text('Now playing\n"{}"\nby {}'.format(track["item"]["name"],
                                                                          track["item"]["artists"][0]["name"]))
    except:
        await update.message.reply_text('Nothing is currently playing.')


def _get_climate_data():
    try:
        conn = sqlite3.connect("climate.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT temperature, co2, humidity FROM climate_data ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            # row = (temp, co2, humidity)
            return [float(row[0]), int(row[1]), float(row[2])]
        else:
            return [0, 0, 0]
    except Exception as e:
        print("DB error:", e)
        return [0, 0, 0]


def _get_ppl():
    """
    Reads the most recent climate data from the guildroom
    and then predicts the amount of people at the guildroom.
    The current model is linear and not very accurate, but it'll do for now.
    """
    co = _get_climate_data()[1]
    if co != 0:
        humans = round(0.018966699 * int(co) - 8.308014998, 2)
    else:
        humans = 0
    return humans


async def people_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns a simple value as the expected occupancy of the guildroom.
    The value is counted in the function above.
    """
    await update.message.reply_text("Guildroom occupancy:\n ~{}".format(_get_ppl()))


async def guild_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns a compilation of the climate data from the guildroom
    Collected with the gmw90 attached to the wall at the guildroom.

    Formatting example:
    CO2: 652 ppm
    Temperature: 22.1 C
    Humidity: 29.6 %
    People: ~9
    """
    co = _get_climate_data()[1]
    temp = _get_climate_data()[0]
    hum = _get_climate_data()[2]
    await update.message.reply_text("CO2: {}ppm\n"
                                    "Temperature: {}°C\n"
                                    "Humidity: {}%\n"
                                    "People: ~{}\n".format(co, temp, hum, _get_ppl()))


async def get_plot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Draws and returns a plot of the climate data from the guildroom.
    Showing the last 24h by default but can be adjusted manually.
    """
    plot_data.plotting()
    pic = open("./plots/newest.png", "rb")
    await update.get_bot().sendPhoto(update.message.chat_id, photo=pic)


async def add_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Adds a quote from a telegram chat to a chat-specific database.
    User needs to reply to a message he wants to quote with the message
    '/addquote'
    """

    # Determining whether the quote is valid with the following if/else clauses.
    # Using command when not replying
    if not update.effective_message.reply_to_message:
        await update.message.reply_text("Please use '/addquote' by replying to a message.")

    # Using command and not replying to a text or a voice message (useless spam, don't want that)
    if not update.message.reply_to_message.text and not context.message.reply_to_message.voice:
        await update.message.reply_text("Please only add text or voice quotes.")

    # Using command without tags on a voice message (can't search non-text entries in db)
    if update.message.reply_to_message.voice and not _get_message_args(update.message.text):
        await update.message.reply_text("Please add search tags after '/addquote' for voice messages.")

    message = update.message
    print(message)
    reply = message.reply_to_message
    print(reply)
    quote_text = reply.text.lower()
    print(quote_text)
    tags = _get_message_args(message.text)
    print(tags)
    message_id = reply.message_id
    print(message_id)
    chat_id = reply.chat.id
    print(chat_id)

    if reply.from_user:
        reply_first_name = reply.from_user.first_name
        reply_last_name = reply.from_user.last_name
        added_by = reply_first_name.lower() + (" " + reply_last_name.lower() if reply_last_name else "")
    else:
        reply_first_name = reply.from_user.first_name
        reply_last_name = reply.from_user.last_name
        added_by = reply_first_name.lower() + (" " + reply_last_name.lower() if reply_last_name else "")

    message_first_name = message.from_user.first_name
    message_last_name = message.from_user.last_name
    said_by = message_first_name.lower() + (" " + message_last_name.lower() if message_last_name else "")
    print(added_by)
    print(said_by)

    said_date = reply.date.strftime("%Y.%m.%d %H:%M")
    print(said_date)
    added_date = message.date.strftime("%Y.%m.%d %H:%M")
    print(added_date)

    conn, c = _init_db(config.quotedb)
    try:
        c.execute("INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (quote_text, tags, message_id, chat_id, said_by, added_by, said_date, added_date))
        conn.commit()
        await update.message.reply_text("Quote added.")
    except Exception as e:
        if str(e).startswith("UNIQUE constraint failed") and _get_message_args(update.message.text):
            old_tags = c.execute("SELECT tags FROM quotes WHERE message_id = ?", (str(message_id),)).fetchone()
            new_tags = " ".join(list(set(old_tags[0].split() + tags.split())))
            c.execute("UPDATE quotes SET tags = ? WHERE message_id = ?", (new_tags, str(message_id)))
            conn.commit()
            await update.message.reply_text("Message already added! Tags updated.")
        elif str(e).startswith("UNIQUE constraint failed"):
            await update.message.reply_text("Error adding quote:\nMessage already added!")
        else:
            await update.message.reply_text("Error adding quote:\n{}".format(e))
    finally:
        conn.close()


async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Forwards a quote to a chat.
    If there are words after '/quote', these are considered
    search arguments and are used for limiting the search and
    identifying quotes from the db based on the quotee, text
    in quote or tags.
    """
    await update.message.reply_text("Searching quote")


async def list_quotes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Lists all quotes of a user to him in private chat
    """
    await update.message.reply_text("Getting a list of quotes")


async def delete_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Deletes a quote by same user requesting deletion
    """
    await update.message.reply_text("Deleting a quote")


async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a joke to a chat.
    If there are words after '/puuta', these are considered
    search arguments and are used for limiting the search and
    identifying quotes from the db based on the text
    in joke or tags.
    """
    await update.message.reply_text("Getting joke")


async def add_joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Adds a joke from a telegram chat to generic database.
    User can reply to a joke or add one as an argument after
    the command '/lisaapuuta'
    """
    await update.message.reply_text("Adding joke")

async def get_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns the current coffee level in the guildroom.
    """
    try:
        result = coffee_analysis.get_coffee_analysis()
        await update.message.reply_text(f"Coffee level (dark pixels): {result}")
    except Exception as e:
        await update.message.reply_text(f"Error fetching or analyzing coffee image: {e}")
    

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


# Starting and running the bot from here
def main() -> None:

    # Create databases if they don't already exist
    if not os.path.isfile(config.quotedb):
        _create_db(config.quotedb, config.init_quote_db)
    if not os.path.isfile(config.jokedb):
        _create_db(config.jokedb, config.init_joke_db)
    if not os.path.isfile(config.climatedb):
        _create_db(config.climatedb, config.climate_joke_db)

    # Create the Application and pass it your bot's token (found int the config-file)
    application = Application.builder().token(config.kiltistoken).build()

    # On different commands, answer in Telegram accordingly.
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("music", music))
    application.add_handler(CommandHandler("stalk", people_count))
    application.add_handler(CommandHandler("numbers", guild_data))
    application.add_handler(CommandHandler("plot", get_plot))
    application.add_handler(CommandHandler("addquote", add_quote))
    application.add_handler(CommandHandler("quote", quote))
    application.add_handler(CommandHandler("listquotes", list_quotes))
    application.add_handler(CommandHandler("deletequote", delete_quote))
    application.add_handler(CommandHandler("joke", joke))
    application.add_handler(CommandHandler("addjoke", add_joke))
    application.add_handler(CommandHandler("coffee", get_coffee))

    # For debugging
    # application.add_handler(CommandHandler("echo", echo))

    # Add an error handler.
    application.add_error_handler(error)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

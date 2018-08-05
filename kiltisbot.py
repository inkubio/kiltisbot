from uuid import uuid4
import re
from telegram import InlineQueryResultArticle, \
    InlineQueryResultPhoto, \
    ParseMode, \
    InputTextMessageContent
from telegram.ext import Updater, \
    InlineQueryHandler, \
    CommandHandler, \
    MessageHandler, \
    Filters
import logging
import urllib.request
import os
import config
import sqlite3
from datetime import datetime
import random
import requests

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
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
    except:
        print("Failed to initialize database!")
        conn.close()
        quit()


def _get_message_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    return " ".join([tag for tag in string.split() if tag[0] != '/'])

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.


def _get_now_playing():
    url = 'https://www.inkubio.fi/kiltiscam/spotify_data.JSON'
    data = requests.get(url).json()

    return data

def robin(bot, update):

    songs = _get_now_playing()
    if songs['status'] == 'Playing':
        bot.sendMessage(update.message.chat.id, 'Now playing {} by {}'.format(songs['songs'][0]['name'], songs['songs'][0]['artist']))
    else:
        bot.sendMessage(update.message.chat.id, 'Nothing seems to be playing.\n')

def _get_img_from_kiltiscam():
    """
    Grabs current kiltiscam image from server
    """
    cur_path = os.path.dirname(__file__)
    img_path = os.path.relpath("../../projektit/kiltiscam/kiltahuone.jpg")
    f = open(img_path, "rb")
    return f


def stalk(bot, update):
    """
    Command to post current kiltiscam image
    """
    img = _get_img_from_kiltiscam()
    bot.sendPhoto(update.message.chat_id, photo=img)
    img.close()


def add_quote(bot, update):
    """
    Adds a quote from a telegram chat to a chat-specific database.
    User needs to reply to a message he wants to quote with the message
    '/addquote'
    """

    # Using command when not replying (unsupported functionality, current is enough)
    if not update.message.reply_to_message:
        bot.sendMessage(update.message.chat.id,
                        "Please use '/addquote' by replying to a message.",
                        reply_to_message_id=update.message.message_id)
        return

    # Using command and not replying to a text or a voice message (useless spam, don't want that)
    if not update.message.reply_to_message.text and not update.message.reply_to_message.voice:
        bot.sendMessage(update.message.chat.id,
                        "Please only add text or voice quotes.",
                        reply_to_message_id=update.message.message_id)
        return

    # Using command without tags on a voice message (can't search non-text entries in db)
    if update.message.reply_to_message.voice and not _get_message_args(update.message.text):
        bot.sendMessage(update.message.chat.id,
                        "Please add search tags after '/addquote' for voice messages.",
                        reply_to_message_id=update.message.message_id)
        return

    message = update.message
    reply = message.reply_to_message
    quote = reply.text.lower()
    tags = _get_message_args(message.text)
    message_id = reply.message_id
    chat_id = reply.chat.id

    if reply.forward_from:
        reply_first_name = reply.forward_from.first_name
        reply_last_name = reply.forward_from.last_name
        reply_name = reply_first_name.lower() + (" " + reply_last_name.lower() if reply_last_name else "")
    else:
        reply_first_name = reply.from_user.first_name
        reply_last_name = reply.from_user.last_name
        reply_name = reply_first_name.lower() + (" " + reply_last_name.lower() if reply_last_name else "")
    message_first_name = message.from_user.first_name
    message_last_name = message.from_user.last_name
    message_name = message_first_name.lower() + (" " + message_last_name.lower() if message_last_name else "")

    said_by = reply_name
    added_by = message_name
    date_added = int(message.date.timestamp())
    date_said = int(reply.date.timestamp())

    conn, c = _init_db(config.quotedb)
    try:
        c.execute("INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (quote, tags, message_id, chat_id, said_by, added_by, date_said, date_added))
        conn.commit()
        bot.sendMessage(chat_id, "Quote added.")
    except Exception as e:
        if str(e).startswith("UNIQUE constraint failed"):
            bot.sendMessage(chat_id, "Error adding quote:\nMessage already added!")
        else:
            bot.sendMessage(chat_id, "Error adding quote:\n{}".format(e))
    finally:
        conn.close()


def _search_msg_id(chat_id, args):
    """
    Fetches a random possible meaning of search term
    (only text, first name and text or full name and text)
    one arg at a time
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_db(config.quotedb)
    results = []
    try:
        for arg in args:
            ret = c.execute("""
                            SELECT message_id
                            FROM quotes
                            WHERE chat_id=:id
                            AND said_by LIKE :arg
                            """,
                            {"id": str(chat_id), "arg": like(arg)}
                            ).fetchall()
            ret += c.execute("""
                             SELECT message_id
                             FROM quotes
                             WHERE chat_id=:id
                             AND quote LIKE :arg
                             """,
                             {"id": str(chat_id), "arg": like(arg)}
                             ).fetchall()
            ret += c.execute("""
                             SELECT message_id
                             FROM quotes
                             WHERE chat_id=:id
                             AND tags LIKE :arg
                             """,
                             {"id": str(chat_id), "arg": like(arg)}
                             ).fetchall()
            results.extend(ret)
    finally:
        conn.close()

    id = random.choice(results)[0] if results else None
    return id


def _random_msg_id(chat_id):
    """
    Returns a random quote from the same chat as the request
    """
    conn, c = _init_db(config.quotedb)
    ret = None
    try:
        ret = c.execute("""
                        SELECT message_id
                        FROM quotes
                        WHERE chat_id=?
                        ORDER BY RANDOM() LIMIT 1
                        """,
                        (str(chat_id),)).fetchone()
    finally:
        conn.close()
    return ret[0] if ret else None


def get_quote(bot, update):
    """
    Forwards a quote to a chat.
    If there are words after '/quote', these are considered
    search arguments and are used for limiting the search and
    identifying quotes from the db based on the quotee, text
    in quote or tags.
    """
    msg = update.message.text.lower()
    chat_id = update.message.chat.id

    arglist = _get_message_args(update.message.text).split()
    if arglist:
        msg_id = _search_msg_id(chat_id, arglist)
    else:
        msg_id = _random_msg_id(chat_id)

    if msg_id:
        bot.forwardMessage(chat_id=chat_id, from_chat_id=chat_id, message_id=msg_id)
    else:
        bot.sendMessage(chat_id, "Can't find a quote",
                        reply_to_message_id=update.message.message_id)


def list_quotes(bot, update):
    """
    Lists all quotes of a user to him in private chat
    """
    if update.message.chat.type != "private":
        return
    conn, c = _init_db(config.quotedb)
    try:
        ret = c.execute("""
                        SELECT quote, tags, message_id
                        FROM quotes
                        WHERE said_by = ?
                        """,
                        (update.message.chat.first_name.lower() + " " +
                         update.message.chat.last_name.lower(),)).fetchall()

        text = "\n\n".join([str(i + 1) + ":\nQuote: " + (t[0] if t[0] else "VoiceMessage") +
                            "\nTags: " + (t[1] if t[1] else "None") +
                            "\nID: " + str(t[2]) for i, t in enumerate(ret)])
        bot.sendMessage(update.message.chat.id, text)
    finally:
        conn.close()


def delete_quote(bot, update):
    """
    Deletes a quote by same user requesting deletion
    """
    if update.message.chat.type != "private":
        return
    text = update.message.text.lower().split()
    text = " ".join(text[1:])
    conn, c = _init_db(config.quotedb)
    try:
        ret = c.execute("""
                        DELETE FROM quotes
                        WHERE said_by=?
                        AND message_id=?
                        """,
                        (update.message.chat.first_name.lower() + " " +
                         update.message.chat.last_name.lower(),
                         text)).fetchall()
        conn.commit()
        bot.sendMessage(update.message.chat.id, "Quote deleted.")
    except:
        bot.sendMessage(update.message.chat.id, "Couldn't delete quote:\n{}"
                        .format(text))
    finally:
        conn.close()


def add_joke(bot, update):
    """
    Adds a joke from a telegram chat to generic database.
    User can reply to a joke or add one as an argument after
    the command '/lisaapuuta'
    """

    message = update.message
    reply = message.reply_to_message

    if reply:  # Two branches: either adding via a reply, or adding as a single message
        if not reply.text:  # Using command and not replying to a text message
            bot.sendMessage(message.chat.id,
                            "Please only add text-based jokes.",
                            reply_to_message_id=message.message_id)
            return
        joke = reply.text
        tags = _get_message_args(message.text)

    else:  # Not a reply
        joke = _get_message_args(message.text)
        tags = ""
        if not joke:
            bot.sendMessage(message.chat.id,
                            "Please use '/lisaapuuta' by replying to a message or with a joke as an argument.",
                            reply_to_message_id=message.message_id)
            return

    chat_id = message.chat.id
    date_added = int(message.date.timestamp())
    said_by = message.from_user.first_name.lower() + " " + message.from_user.last_name.lower()

    conn, c = _init_db(config.jokedb)
    try:
        c.execute("INSERT INTO jokes VALUES (?, ?, ?)",
                  (joke, tags, date_added))
        conn.commit()
        if said_by == "roope vesterinen" or said_by == "eero linna":
            bot.sendMessage(chat_id, "Ulos.")
        else:
            bot.sendMessage(chat_id, "Puu added.")
    except Exception as e:
        bot.sendMessage(chat_id, "Error adding puuta:\n{}".format(e))
    finally:
        conn.close()


def _search_joke(args):
    """
    Fetches a random joke based on arguments, which are matched
    with text of joke or tags of joke
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_db(config.jokedb)
    results = []
    try:
        for arg in args:
            ret = c.execute("""
                             SELECT joke
                             FROM jokes
                             WHERE joke LIKE :arg
                             """,
                             {"arg": like(arg)}
                             ).fetchall()
            ret += c.execute("""
                             SELECT joke
                             FROM jokes
                             WHERE tags LIKE :arg
                             """,
                             {"arg": like(arg)}
                             ).fetchall()
            results.extend(ret)
    finally:
        conn.close()

    joke = random.choice(results)[0] if results else None
    return joke


def _random_joke():
    """
    Returns a random joke
    """
    conn, c = _init_db(config.jokedb)
    ret = None
    try:
        ret = c.execute("""
                        SELECT joke
                        FROM jokes
                        ORDER BY RANDOM() LIMIT 1
                        """).fetchone()
    finally:
        conn.close()
    return ret[0] if ret else None


def get_joke(bot, update):
    """
    Sends a joke to a chat.
    If there are words after '/puuta', these are considered
    search arguments and are used for limiting the search and
    identifying quotes from the db based on the text
    in joke or tags.
    """
    msg = update.message.text.lower()
    chat_id = update.message.chat.id

    arglist = _get_message_args(update.message.text).split()
    if arglist:
        joke = _search_joke(arglist)
    else:
        joke = _random_joke()

    if joke:
        bot.sendMessage(chat_id, joke)
    else:
        bot.sendMessage(chat_id, "Not enough puuta.",
                        reply_to_message_id=update.message.message_id)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def echo(bot, update):
    """
    Debugging print function
    """
    print(update)


def main():
    if not os.path.isfile(config.quotedb):
        _create_db(config.quotedb, config.init_quote_db)
    if not os.path.isfile(config.jokedb):
        _create_db(config.jokedb, config.init_joke_db)

    updater = Updater(config.kiltistoken)  # Create the Updater and pass it your bot's token.
    dp = updater.dispatcher  # Get the dispatcher to register handlers

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("stalk", stalk))
    dp.add_handler(CommandHandler("addquote", add_quote))
    dp.add_handler(CommandHandler("quote", get_quote))
    dp.add_handler(CommandHandler("listquotes", list_quotes))
    dp.add_handler(CommandHandler("deletequote", delete_quote))
    dp.add_handler(CommandHandler("puuta", get_joke))
    dp.add_handler(CommandHandler("lisaapuuta", add_joke))
    dp.add_handler(CommandHandler("robin", robin))
    # dp.add_handler(MessageHandler("", echo))  # Debug printing
    dp.add_error_handler(error)

    updater.start_polling()  # Start the Bot

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

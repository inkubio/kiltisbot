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

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def _init_quote_db():
    """
    Initializes database connection
    Returns cursor to interact with db
    """
    connection = sqlite3.connect("quote.db")
    return connection, connection.cursor()

'''
def _get_img_from_kiltiscam():
    """
    Grabs current kiltiscam image from server
    """
    cur_path = os.path.dirname(__file__)
    img_path = os.path.relpath("../kiltiscam/kiltahuone.jpg")
    f = open(img_path, "rb")
    return f


def _get_img_from_url(url):
    """
    Deprecated old function that grabs the image from
    inkubio.fi/kiltiscam/kiltahuone.jpg
    """
    img = urllib.request.urlopen(url).read()
    with open('out.jpg','wb') as f:
        f.write(img)
        i = open('out.jpg', 'rb')
        return i

'''
# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.

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
    if not update.message.reply_to_message:
        print(update)
        bot.sendMessage(update.message.chat.id,
                        "Please use '/addquote' by replying to a message.",
                        reply_to_message_id=update.message.message_id)
        return

    message = update.message
    reply = message.reply_to_message
    quote = reply.text.lower()
    message_id = reply.message_id
    chat_id = reply.chat.id
    said_by = reply.from_user.first_name.lower() + " " + reply.from_user.last_name.lower()
    added_by = message.from_user.first_name.lower() + " " + message.from_user.last_name.lower()
    date_added = int(message.date.timestamp())
    date_said = int(reply.date.timestamp())

    conn, c = _init_quote_db()
    try:
        c.execute("INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?)",
            (quote, message_id, chat_id, said_by, added_by, date_said, date_added))
        conn.commit()
        bot.sendMessage(chat_id, "Quote added.")
    except Exception as e:
        bot.sendMessage(chat_id, "Error adding quote:\n{}".format(e))
    finally:
        conn.close()


def _search_msg_id(chat_id, args):
    """
    Fetches a random possible meaning of search term
    (only text, first name and text or full name and text)
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_quote_db()
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
            results.extend(ret)
    finally:
        conn.close()

    id = random.choice(results)[0] if results else None
    return id


def _random_msg_id(chat_id):
    conn, c = _init_quote_db()
    ret = None
    try:
        ret = c.execute("""
                        SELECT message_id
                        FROM quotes
                        WHERE chat_id=?
                        ORDER BY RANDOM() LIMIT 1
                        """,
                        (str(chat_id),)).fetchone()
        #except:
        #    print("voivittu")
    finally:
        conn.close()
    return ret[0] if ret else None


def get_quote(bot, update):
    msg = update.message.text.lower()
    chat_id = update.message.chat.id

    args = None if len(msg.split()) == 1 else msg.split()[1:]
    if args:
        msg_id = _search_msg_id(chat_id, args)
    else:
        msg_id = _random_msg_id(chat_id)

    if msg_id:
        bot.forwardMessage(chat_id=chat_id, from_chat_id=chat_id, message_id=msg_id)
    else:
        bot.sendMessage(chat_id, "Can't find a quote")


# Experimental functionality, currently disabled
"""
def inlinequery(bot, update):
    query = update.inline_query.query
    results = []

    results.append(InlineQueryResultPhoto(id=uuid4(),
                                            photo_url="http://www.inkubio.fi/kiltiscam/kiltahuone.jpg",
                                            thumb_url="http://www.inkubio.fi/kiltiscam/kiltahuone.jpg"))

    results.append(InlineQueryResultPhoto(id=uuid4(),
                                            photo_url="http://ruutu.hut.fi/pics/30-Jonotilanne.jpg",
                                            thumb_url="http://ruutu.hut.fi/pics/30-Jonotilanne.jpg"))

    bot.answerInlineQuery(update.inline_query.id, results=results)
"""

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(config.kahmytoken)

    # List for pending quote additions
    global quote_queue
    quote_queue = {}

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("stalk", stalk))
    dp.add_handler(CommandHandler("addquote", add_quote))
    dp.add_handler(CommandHandler("quote", get_quote))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(InlineQueryHandler(inlinequery))

    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

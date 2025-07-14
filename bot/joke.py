import random
import sqlite3
import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from db_utils import jokedb, _init_db
from logger import logger


def _get_message_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    return " ".join([tag for tag in string.split() if tag[0] != '/'])


async def add_joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Adds a joke from a telegram chat to generic database.
    User can reply to a joke or add one as an argument after
    the command '/addjoke'
    """

    message = update.message
    reply = message.reply_to_message

    if reply:  # Two branches: either adding via a reply, or adding as a single message
        if not reply.text:  # Using command and not replying to a text message
            await update.message.reply_text("💡 Please only add text-based jokes 💡",
                            reply_to_message_id=message.message_id)
            return
        joke = reply.text
        tags = _get_message_args(message.text)

    else:  # Not a reply
        joke = _get_message_args(message.text)
        tags = ""
        if not joke:
            await update.message.reply_text("💡 Please use /addjoke by replying to a message 💡\n"
                                            "Or or by using a joke as an argument after it.\n"
                                            "<b>Example:</b> /addjoke haha funny :D",
                                            reply_to_message_id=message.message_id,
                                            parse_mode="HTML")
            return

    date_added = int(message.date.timestamp())

    conn, c = _init_db(jokedb)
    try:
        c.execute("INSERT INTO jokes VALUES (?, ?, ?)",
                  (joke, tags, date_added))
        conn.commit()
        await update.message.reply_text("✅ Joke added ✅")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error adding joke ⚠️"
                                        f"\n{e}")
    finally:
        conn.close()


def _search_joke(args):
    """
    Fetches a random joke based on arguments, which are matched
    with text of joke or tags of a joke
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_db(jokedb)
    results = []
    try:
        for arg in args:
            ret = c.execute("""
                             SELECT joke_text
                             FROM jokes
                             WHERE joke_text LIKE :arg
                             """,
                             {"arg": like(arg)}
                             ).fetchall()
            ret += c.execute("""
                             SELECT joke_text
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
    conn, c = _init_db(jokedb)
    ret = None
    try:
        ret = c.execute("""
                        SELECT joke_text
                        FROM jokes
                        ORDER BY RANDOM() LIMIT 1
                        """).fetchone()
    finally:
        conn.close()
    return ret[0] if ret else None


async def get_joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends a joke to a chat.
    If there are words after '/joke', these are considered
    search arguments and are used for limiting the search and
    identifying quotes from the db based on the text
    in joke or tags.
    """
    try:
        arglist = _get_message_args(update.message.text).split()
        if arglist:
            joke = _search_joke(arglist)
        else:
            joke = _random_joke()

        if joke:
            await update.message.reply_text(joke)
        else:
            await update.message.reply_text("🛑 No jokes 🛑",
                            reply_to_message_id=update.message.message_id)
    except Exception as e:
        logger.error("Error in get_joke: %s", e)
        await update.message.reply_text("🤖️ Something went wrong 🤖")

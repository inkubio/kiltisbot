import random
import sqlite3
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import config
from db_utils import quotedb, _init_db
from logger import logger

def _get_message_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    return " ".join([tag for tag in string.split() if tag[0] != '/'])

def _search_msg_id(chat_id, args):
    """
    Fetches a random possible meaning of search term
    (only text, first name and text or full name and text)
    one arg at a time. For getting quotes.
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_db(quotedb)
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
                             AND quote_text LIKE :arg
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
    conn, c = _init_db(quotedb)
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
    if not update.message.reply_to_message.text and not update.message.reply_to_message.voice:
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
        last_name = reply.from_user.last_name or ""
        added_by = reply_first_name.lower() + (" " + reply_last_name.lower() if reply_last_name else "")
    else:
        reply_first_name = reply.from_user.first_name
        reply_last_name = reply.from_user.last_name
        added_by = reply_first_name.lower() + (" " + reply_last_name.lower() if reply_last_name else "")

    message_first_name = message.from_user.first_name
    message_last_name = message.from_user.last_name or ""
    said_by = message_first_name.lower() + (" " + message_last_name.lower() if message_last_name else "")
    print(added_by)
    print(said_by)

    said_date = reply.date.strftime("%Y.%m.%d %H:%M")
    print(said_date)
    added_date = message.date.strftime("%Y.%m.%d %H:%M")
    print(added_date)

    conn, c = _init_db(quotedb)
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


async def get_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await context.bot.forwardMessage(chat_id=chat_id, from_chat_id=chat_id, message_id=msg_id)
    else:
        await update.message.reply_text("Can't find a quote",
                        reply_to_message_id=update.message.message_id)


async def list_quotes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Lists all quotes of a user to them in private chat
    """
    if update.message.chat.type != "private":
        return
    conn, c = _init_db(quotedb)
    try:
        first_name = update.message.chat.first_name or ""
        last_name = update.message.chat.last_name or ""
        user_fullname = (first_name + " " + last_name).strip().lower()

        ret = c.execute("""
                        SELECT quote_text, tags, message_id
                        FROM quotes
                        WHERE said_by = ?
                        """,
                        (user_fullname,)).fetchall()
        if not ret:
            await update.message.reply_text("You have no quotes saved.")
            return

        text = "\n\n".join([
            f"{i + 1}:\nQuote: {(t[0] if t[0] else 'VoiceMessage')}\nTags: {(t[1] if t[1] else 'None')}\nID: {t[2]}"
            for i, t in enumerate(ret)
        ])
        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("Error in list_quotes")
        await update.message.reply_text("An error occurred while listing your quotes.")
    finally:
        if conn:
            conn.close()

async def delete_quote(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    """
    Deletes a quote by same user requesting deletion
    """
    if update.message.chat.type != "private":
        return

    conn, c = _init_db(quotedb)
    try:
        args = update.message.text.strip().split()
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text(
                "Käyttö: /deletequote [lainauksen ID]\n"
                "Saat ID:n komennolla /listquotes tai vastaamalla viestiin, jossa lainaus näkyy."
            )
            return

        target_id = int(args[1])
        user = update.message.chat.first_name.lower() + " " + update.message.chat.last_name.lower()

        deleted = c.execute("""
            DELETE FROM quotes
            WHERE said_by = ?
            AND message_id = ?
        """, (user, target_id))
        conn.commit()

        if deleted.rowcount > 0:
            await update.message.reply_text("Lainaus poistettu.")
        else:
            await update.message.reply_text(
                "Lainausta ei löytynyt ID:llä tai se ei ole sinun.\n"
                "Tarkista ID komennolla /listquotes."
            )

    except Exception as e:
        await update.message.reply_text(f"Virhe poistaessa lainausta: {e}")
    finally:
        conn.close()
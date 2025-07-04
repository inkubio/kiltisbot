import random
import sqlite3
import logging
from telegram import Update
from telegram.ext import ContextTypes
import config
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
        return

    reply = update.message.reply_to_message

    # Using command and not replying to a text or a voice message
    if not reply.text and not reply.voice:
        await update.message.reply_text("Please only add text or voice quotes.")
        return

    # Using command without tags on a voice message
    if reply.voice and not _get_message_args(update.message.text):
        await update.message.reply_text("Please add search tags after '/addquote' for voice messages.")
        return

    message = update.message
    quote_text = reply.text.lower() if reply.text else "[voice message]"
    tags = _get_message_args(message.text)
    message_id = reply.message_id
    chat_id = reply.chat.id

    # Get "added_by" from the message being replied to
    if reply.from_user:
        first_name = reply.from_user.first_name or ""
        last_name = reply.from_user.last_name or ""
        added_by = f"{first_name} {last_name}".strip().lower()
    else:
        added_by = "unknown"

    # Get "said_by" from the person who issued the command
    if message.from_user:
        sfname = message.from_user.first_name or ""
        slname = message.from_user.last_name or ""
        said_by = f"{sfname} {slname}".strip().lower()
    else:
        said_by = "unknown"

    said_date = reply.date.strftime("%Y.%m.%d %H:%M")
    added_date = message.date.strftime("%Y.%m.%d %H:%M")

    conn, c = _init_db(quotedb)
    try:
        c.execute("INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (quote_text, tags, message_id, chat_id, said_by, added_by, said_date, added_date))
        conn.commit()
        await update.message.reply_text("Quote added.")
    except Exception as e:
        logger.error("Error while adding quote: %s", e)
        if str(e).startswith("UNIQUE constraint failed") and tags:
            try:
                old_tags = c.execute("SELECT tags FROM quotes WHERE message_id = ?", (str(message_id),)).fetchone()
                if old_tags:
                    new_tags = " ".join(sorted(set(old_tags[0].split() + tags.split())))
                    c.execute("UPDATE quotes SET tags = ? WHERE message_id = ?", (new_tags, str(message_id)))
                    conn.commit()
                    await update.message.reply_text("Message already added! Tags updated.")
                else:
                    await update.message.reply_text("Could not update tags: quote not found.")
            except Exception as tag_err:
                logger.error("Tag update failed: %s", tag_err)
                await update.message.reply_text("Error updating tags.")
        elif str(e).startswith("UNIQUE constraint failed"):
            await update.message.reply_text("Error adding quote:\nMessage already added!")
        else:
            await update.message.reply_text(f"Error adding quote:\n{e}")
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
                "How to use: /deletequote [quote ID]\n"
                "You can get quote ID for your messages by using /listquotes"
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
            await update.message.reply_text("Quote removed.")
        else:
            await update.message.reply_text(
                "Quote was not found with that ID or it's not your quote.\n"
                "Check ID with /listquotes."
            )

    except Exception as e:
        await update.message.reply_text(f"Error removing quote: {e}")
    finally:
        conn.close()
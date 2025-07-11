import random
import sqlite3
import logging
from typing import Any, Dict, List
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import config
from db_utils import songdb, _init_db
from logger import logger


def _get_add_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    try:
        lines = string.strip().splitlines()
        title_line = next(line for line in lines if line.startswith("Title:"))
        melody_line = next(line for line in lines if line.startswith("Melody:"))
        writers_line = next(line for line in lines if line.startswith("Writers:"))
        composers_line = next(line for line in lines if line.startswith("Composers:"))
        song_number_line = next(line for line in lines if line.startswith("Song number:"))
        page_number_line = next(line for line in lines if line.startswith("Page number:"))
        lyrics_start = lines.index("Lyrics:") + 1
        lyrics = "\n".join(lines[lyrics_start:])

        title = title_line.replace("Title:", "").strip()
        melody = melody_line.replace("Melody:", "").strip()
        writers = writers_line.replace("Writers:", "").strip()
        composers = composers_line.replace("Composers:", "").strip()
        song_number = song_number_line.replace("Song number:", "").strip()
        page_number = page_number_line.replace("Page number:", "").strip()

        return title, melody, writers, composers, song_number, page_number, lyrics
    except Exception as e:
        return None


def _get_message_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    return " ".join([tag for tag in string.split() if tag[0] != '/'])


def _search_song(args) -> List[Dict[str, Any]]:
    """
    Fetches possible matches based on song name and lyrics.
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_db(songdb)
    results = []
    try:
        for arg in args:
            ret = c.execute("""
                            SELECT song_name
                            FROM songs
                            AND song_name LIKE :arg
                            """,
                             {"arg": like(arg)}
                             ).fetchall()
            ret += c.execute("""
                             SELECT song_name
                             FROM songs
                             AND song_text LIKE :arg
                             """,
                             {"arg": like(arg)}
                             ).fetchall()
            results.extend(ret)
    finally:
        conn.close()

    matches = results if results else None
    return matches


def _random_song():
    """
    Returns a random quote from the same chat as the request
    """
    conn, c = _init_db(songdb)
    ret = None
    try:
        ret = c.execute("""
                        SELECT song_name
                        FROM songs
                        ORDER BY RANDOM() LIMIT 1
                        """).fetchone()
    finally:
        conn.close()
    return ret[0] if ret else None


async def add_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Adds a quote from a telegram chat to a chat-specific database.
    User needs to reply to a message he wants to quote with the message
    '/addquote'
    """
    if update.message.chat.type != "private":
        return
    conn, c = _init_db(songdb)

    message = update.message
    raw_text = message.text

    if not raw_text or raw_text.strip() == "/addsong":
        await message.reply_text("Please include song info after /addsong:\n"
                                 "Title: ...\n"
                                 "Melody: ...\n"
                                 "Writers: ...\n"
                                 "Composers: ...\n"
                                 "Song number: ...\n"
                                 "Page number: ...\n"
                                 "Lyrics:\n...")
        return

    args = _get_add_args(raw_text)
    if not args:
        await message.reply_text("Invalid song format. Please include:\n"
                                 "Title: ...\n"
                                 "Melody: ...\n"
                                 "Writers: ...\n"
                                 "Composers: ...\n"
                                 "Song number: ...\n"
                                 "Page number: ...\n"
                                 "Lyrics:\n...")

    title, melody, writers, composers, song_number, page_number, lyrics = args

    conn, c = _init_db(songdb)
    try:
        c.execute("INSERT INTO songs VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (title, melody, writers, composers, song_number, page_number, lyrics))
        conn.commit()
        await update.message.reply_text(f"🎵 Song '{title}' added.")
    except Exception as e:
        logger.error("Error while adding song: %s", e)
        if str(e).startswith("UNIQUE constraint failed"):
            await update.message.reply_text("Song already added.")
        else:
            await update.message.reply_text(f"Error while adding song: {e}")
    finally:
        conn.close()


async def send_long_message(update: Update, text: str, parse_mode=ParseMode.HTML) -> None:
    """
    Send a message, splitting it if it's too long.
    ps. thank you FK
    """
    max_length = 4000  # Leave some buffer under Telegram's 4096 limit

    if len(text) <= max_length:
        await update.message.reply_text(
            text, parse_mode=parse_mode, disable_web_page_preview=True
        )
        return

    # Split into chunks
    chunks = []
    remaining = text

    while len(remaining) > max_length:
        # Find a good place to split (prefer line breaks)
        chunk = remaining[:max_length]
        last_newline = chunk.rfind("\n\n")  # Look for paragraph breaks first
        if last_newline == -1:
            last_newline = chunk.rfind("\n")  # Then any line break

        if last_newline > max_length - 200:  # If we found a good break point
            split_point = last_newline
        else:
            split_point = max_length

        chunks.append(remaining[:split_point])
        remaining = remaining[split_point:].lstrip()

    if remaining:
        chunks.append(remaining)

    # Send each chunk
    for i, chunk in enumerate(chunks):
        if i == 0:
            # First chunk - send as reply
            await update.message.reply_text(
                chunk, parse_mode=parse_mode, disable_web_page_preview=True
            )
        else:
            # Subsequent chunks - send as follow-up
            await update.effective_chat.send_message(
                chunk, parse_mode=parse_mode, disable_web_page_preview=True
            )


async def get_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Forwards a quote to a chat.
    If there are words after '/quote', these are considered
    search arguments and are used for limiting the search and
    identifying quotes from the db based on the quotee, text
    in quote or tags.
    """
    msg = update.message.text.lower()
    chat_id = update.message.chat.id

    if update.message.chat.type != "private":
        return
    conn, c = _init_db(songdb)

    arglist = _get_message_args(update.message.text).split()
    match_songs = _search_song(arglist)

    if not match_songs:
        await update.message.reply_text(
            f"🔍 No results for: <b>{arglist}</b>\n\n"
            "Try different search terms!",
            parse_mode=ParseMode.HTML,
        )
        return

    ret = c.execute("""
                            SELECT song_name, song_melody, song_writers, song_composers, song_song_number, song_page_number, song_lyrics)
                            FROM songs
                            WHERE song_name = ?
                            """,
                    (match_songs[0],)).fetchall()

    if len(match_songs) == 1:
        name = ret[0][0]
        melody = ret[0][1]
        writers = ret[0][2]
        composers = ret[0][3]
        song_number = ret[0][4]
        page_number = ret[0][5]
        lyrics = ret[0][6]

        text = f"🎵 <b>{name}</b>\n"
        metadata = []
        if melody:
            metadata.append(f"🎼 Mel: {melody}")
        if writers:
            metadata.append(f"✍️ San: {writers}")
        if composers:
            metadata.append(f"🎹 Sov: {composers}")
        if song_number:
            metadata.append(f"Laulu nro {melody}")
        if page_number:
            metadata.append(f"Sivu {page_number}")

        if metadata:
            text += "\n" + "\n".join(metadata) + "\n"

        text += f"\n{lyrics}"
        await send_long_message(update, text)
    else:
        text = f"🎵 <b>Found {len(match_songs)} songs for the search:</b> {arglist}"
        for i, song in enumerate(ret):



async def delete_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
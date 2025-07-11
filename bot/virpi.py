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

"""
Implementation of songbook database and it's usage trhough telegram.
Huge thanks to Guild of Physics and their Fiisubot for inspiring and helping with this! <3
"""

def _get_add_args(string):
    """
    Returns a list of specified arguments given by the user. Arguments are metadata about a song.
    """
    try:
        lines = string.strip().splitlines()

        name = ""
        melody = ""
        writers = ""
        composers = ""
        song_number = ""
        page_number = ""
        lyrics = ""

        for i, line in enumerate(lines):
            if line.lower().startswith("Name:"):
                name = line.split(":", 1)[1].strip()
            elif line.lower().startswith("Melody:"):
                melody = line.split(":", 1)[1].strip()
            elif line.lower().startswith("Writers:"):
                writers = line.split(":", 1)[1].strip()
            elif line.lower().startswith("Composers:"):
                composers = line.split(":", 1)[1].strip()
            elif line.lower().startswith("Song number:"):
                song_number = line.split(":", 1)[1].strip()
            elif line.lower().startswith("Page number:"):
                page_number = line.split(":", 1)[1].strip()
            elif line.lower().startswith("Lyrics:"):
                lyrics = "\n".join(lines[i + 1:]).strip()
                break  # Lyrics is last section

        if not name or not lyrics:
            return None  # these are mandatory

        return name, melody, writers, lyrics, composers, song_number, page_number
    except Exception:
        return None


def _get_message_args(string):
    """
    Returns all args from input string separated with spaces as a string
    """
    return " ".join([tag for tag in string.split() if tag[0] != '/'])


def _search_song(args):
    """
    Fetches possible matches based on song name and lyrics.
    """
    def like(string):
        return "%{}%".format(string)

    conn, c = _init_db(songdb)
    seen_songs = set()
    results = set()

    try:
        for arg in args:
            name_matches = c.execute("""
                            SELECT song_name
                            FROM songs
                            WHERE song_name LIKE :arg
                            """,
                             {"arg": like(arg)}
                             ).fetchall()
            lyric_matches = c.execute("""
                             SELECT song_name
                             FROM songs
                             WHERE song_lyrics LIKE :arg
                             """,
                             {"arg": like(arg)}
                             ).fetchall()
            for row in name_matches + lyric_matches:
                results.add(row[0])
    finally:
        conn.close()

    matches = sorted(results) if results else None
    return matches


async def add_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Adds a song from a private chat with a specified allowed user and adds it to a database.
    """
    if update.message.chat.type != "private":
        return

    if update.message.from_user.id not in config.SONG_MASTERS:
        await update.message.reply_text("Sorry, not allowed to do that ;)")
        return

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
        return

    # Unpack and optionally clean up args
    title, melody, writers, composers, song_number, page_number, lyrics = (
        field.strip() if field else "" for field in args
    )

    conn, c = _init_db(songdb)
    try:
        c.execute("INSERT INTO songs VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (title, melody, writers, composers, song_number, page_number, lyrics))
        conn.commit()
        await update.message.reply_text(f"🎵 Song '{title}' added.")
    except Exception as e:
        logger.error("Error while adding song: %s", e)
        if "UNIQUE constraint failed" in str(e):
            await update.message.reply_text("Song already exists.")
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
    Gets a song from the database and sends it to a chat if exact match is found.
    If not, it sends a truncated list of search results.
    """
    msg = update.message.text
    if not msg:
        return

    conn, c = _init_db(songdb)

    try:
        arglist = _get_message_args(msg).split()
        if not arglist:
            await update.message.reply_text("❗Please include search terms.")
            return

        match_songs = _search_song(arglist)
        if not match_songs:
            await update.message.reply_text(
                f"🔍 No results for: <b>{arglist}</b>\n\n"
                "Try different search terms!",
                parse_mode=ParseMode.HTML,
            )
            return

        placeholders = ','.join('?' for _ in match_songs)
        ret = c.execute(f"""
                            SELECT song_name, song_melody, song_writers, song_composers, song_song_number, song_page_number, song_lyrics
                            FROM songs
                            WHERE song_name IN ({placeholders})
                        """, match_songs).fetchall()

        if len(match_songs) == 1 and ret:
            name, melody, writers, composers, song_number, page_number, lyrics = ret[0]

            text = f"🎵 <b>{name}</b>\n"

            metadata = []
            if melody:
                metadata.append(f"🎼 Mel: {melody}")
            if writers:
                metadata.append(f"✍️ San: {writers}")
            if composers:
                metadata.append(f"🎹 Sov: {composers}")
            if song_number:
                metadata.append(f"Laulu nro {song_number}")
            if page_number:
                metadata.append(f"Sivu {page_number}")

            if metadata:
                text += "\n" + "\n".join(metadata) + "\n"

            text += f"\n{lyrics}"
            await send_long_message(update, text)

        else:
            text = f"🎵 <b>Found {len(match_songs)} songs for the search:</b> {' '.join(arglist)}"

            for i, song in enumerate(ret, 1):
                name = song[0]
                melody = song[1]
                lyrics = song[6]

                metadata_preview = []
                if melody:
                    metadata_preview.append(f"Säv. {melody}")

                lyrics_preview = lyrics.split("\n")[0] if lyrics else "Ei saatavilla :("
                if len(lyrics) > 40:
                    lyrics_preview = lyrics_preview[:40] + "..."

                text += f"{i}. <b>{name}</b>\n"

                if metadata_preview:
                    escaped_metadata = " | ".join(metadata_preview)
                    text += f"   📄 <i>{escaped_metadata}</i>\n"

                text += f"   🎵 <i>{lyrics_preview}</i>\n\n"

            text += "💡 Tarkenna hakua saadaksesi koko laulun!"

            await send_long_message(update, text)
    finally:
        conn.close()


async def delete_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Allows speicied users to delete songs from the database in private chat.
    """

    if update.message.chat.type != "private":
        return

    if update.message.from_user.id not in config.SONG_MASTERS:
        await update.message.reply_text("Sorry, not allowed to do that ;)")
        return

    msg = update.message.text
    query = _get_message_args(msg).strip()

    if not query:
        await update.message.reply_text("Please provide a song name to delete.")
        return

    matches = _search_song(query.split())
    if not matches:
        await update.message.reply_text(f"🔍 No matching song found for '{query}'.")
        return

    conn, c = _init_db(songdb)
    try:
        # Try deleting exact match first
        deleted = c.execute("""
                            DELETE FROM songs 
                            WHERE song_name = ?
                            """, (query,)).rowcount
        if deleted:
            conn.commit()
            await update.message.reply_text(f"🗑️ Song '{query}' deleted.")
        else:
            # If no exact match, suggest alternatives
            options = "\n".join(f"• {name}" for name in matches[:5])
            await update.message.reply_text(
                f"⚠️ No exact match for '{query}'.\n"
                f"Did you mean one of these?\n\n{options}\n\n"
                f"Please retry with the exact title."
            )
    except Exception as e:
        logger.error("Error while deleting song: %s", e)
        await update.message.reply_text("❌ An error occurred while deleting the song.")
    finally:
        conn.close()
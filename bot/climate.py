import sqlite3
import logging
from telegram import Update
from telegram.ext import ContextTypes
from logger import logger
from zoneinfo import ZoneInfo

import plot_data
from datetime import datetime

def _get_climate_data():
    try:
        conn = sqlite3.connect("climate.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT temperature, co2, humidity, timestamp FROM climate_data ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            # row = (temp, co2, humidity, timestamp)
            return [float(row[0]), int(row[1]), float(row[2]), row[3]]
        else:
            return [0, 0, 0, None]
    except Exception as e:
        print("DB error:", e)
        return [0, 0, 0, None]


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
    ts = _get_climate_data()[3]
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    dt_utc = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt_helsinki = dt_utc.astimezone(ZoneInfo("Europe/Helsinki"))
    formatted_dt = dt_helsinki.strftime("%d.%m.%Y at %H:%M")
    await update.message.reply_text("{}\nEstimated occupancy:\n ~{}".format(formatted_dt, _get_ppl()))


async def guild_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns a compilation of the climate data from the guildroom
    Collected with the gmw90 attached to the wall at the guildroom.

    Formatting example:
    03.05.2025 14:54:12
    CO2: 652 ppm
    Temperature: 22.1 C
    Humidity: 29.6 %
    People: ~9
    """
    temp, co, hum, ts = _get_climate_data()
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    dt_utc = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt_helsinki = dt_utc.astimezone(ZoneInfo("Europe/Helsinki"))
    formatted_dt = dt_helsinki.strftime("%d.%m.%Y at %H:%M")
    await update.message.reply_text("{}\n"
                                    "CO2: {}ppm\n"
                                    "Temperature: {}°C\n"
                                    "Humidity: {}%\n"
                                    "People: ~{}\n".format(formatted_dt, co, temp, hum, _get_ppl()))


async def get_plot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Draws and returns a plot of the climate data from the guildroom.
    Showing the last 24h by default but can be adjusted manually.
    """
    try:
        plot_data.plotting()
    except Exception as e:
        await update.message.reply_text(f"Plotting failed: {e}")
        return

    try:
        with open("./plots/newest.png", "rb") as pic:
            await update.get_bot().send_photo(chat_id=update.message.chat_id, photo=pic)
    except Exception as e:
        await update.message.reply_text(f"Sending photo failed: {e}")
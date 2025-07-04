import sqlite3
import logging
from telegram import Update
from telegram.ext import ContextTypes
from logger import logger


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
    temp, co, hum = _get_climate_data()
    await update.message.reply_text("CO2: {}ppm\n"
                                    "Temperature: {}°C\n"
                                    "Humidity: {}%\n"
                                    "People: ~{}\n".format(co, temp, hum, _get_ppl()))


async def get_plot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Draws and returns a plot of the climate data from the guildroom.
    Showing the last 24h by default but can be adjusted manually.
    """
    import plot_data
    try:
        # Generate the plot
        plot_data.plotting()

        plot_path = "./plots/newest.png"
        if not os.path.isfile(plot_path):
            await update.message.reply_text("Plot image not found.")
            return

        # Send the plot image to the user
        with open(plot_path, "rb") as pic:
            await update.get_bot().send_photo(chat_id=update.effective_chat.id, photo=pic)
    except Exception as e:
        # Log or send error message
        await update.message.reply_text(f"Failed to generate plot: {e}")
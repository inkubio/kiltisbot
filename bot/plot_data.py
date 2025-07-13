import os
import sqlite3
from datetime import datetime, timedelta
import pytz
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib import dates, ticker
from zoneinfo import ZoneInfo


def plotting():
    """
    Draws a climate data plot of the last 24h.
    If no data vailable, the plot will be empty.
    """
    # Timezones
    helsinki_tz = pytz.timezone('Europe/Helsinki')

    # Timerange to be the last 24h (in Helsinki time)
    t_end_local = datetime.now(helsinki_tz)
    t_start_local = t_end_local - timedelta(days=1)

    # Timerange in UTC
    t_end_utc = t_end_local.astimezone(pytz.utc)
    t_start_utc = t_start_local.astimezone(pytz.utc)

    # Format timestamps as string for SQL (UTC strings)
    t_start_str = t_start_utc.strftime("%Y-%m-%d %H:%M:%S")
    t_end_str = t_end_utc.strftime("%Y-%m-%d %H:%M:%S")

    # Register datetime converter to ensure correct plotting by matplotlib
    pd.plotting.register_matplotlib_converters()

    # SQL query and connection
    conn = sqlite3.connect("climate.db")

    query = """
        SELECT timestamp, temperature, co2, humidity
        FROM climate_data
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    """

    df = pd.read_sql_query(query, conn, params=(t_start_str, t_end_str))
    conn.close()

    # Convert timestamp column to datetime and localize
    df['time'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert(ZoneInfo("Europe/Helsinki"))

    # Plot data and show results
    fig, axs = plt.subplots(3, 1)
    # Format the shared x-axis and other shared information.
    for ax in axs:
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M", tz=ZoneInfo("Europe/Helsinki")))
        ax.xaxis.set_major_locator(dates.HourLocator(interval=3))
        ax.xaxis.set_minor_locator(dates.HourLocator(interval=1))
        plt.suptitle(t_end_local.strftime('Last 24h of Kiltis %d.%m.%Y at %H:%M:%S'), fontsize=20)
        ax.grid(which="major", axis="x", linestyle="-")
        ax.grid(which="minor", axis="x", linestyle="--")

    # Format the individual subplots and their axis.

    ax = axs[0]
    ax.scatter(x=df.time, y=df.co2, s=2, color='green')
    ax.set_ylabel('CO2 (ppm)')
    ax.yaxis.set_major_locator(ticker.MultipleLocator(base=200))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(base=100))
    ax.grid(which="major", axis="y", linestyle="-")
    ax.grid(which="minor", axis="y", linestyle="--")

    ax = axs[1]
    ax.scatter(x=df.time, y=df.temperature, s=2, color='red')
    ax.set_ylabel('Temp (°C)')
    ax.yaxis.set_major_locator(ticker.MultipleLocator(base=1))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(base=0.5))
    ax.grid(which="major", axis="y", linestyle="-")
    ax.grid(which="minor", axis="y", linestyle="--")

    ax = axs[2]
    ax.scatter(x=df.time, y=df.humidity, s=2, color='blue')
    ax.set_ylabel('Humidity (RH%)')
    ax.yaxis.set_major_locator(ticker.MultipleLocator(base=5))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(base=2.5))
    ax.grid(which="major", axis="y", linestyle="-")
    ax.grid(which="minor", axis="y", linestyle="--")

    os.makedirs('plots', exist_ok=True)
    # Save the figure as a png to a location
    plt.savefig(os.path.join('plots', 'newest.png'))

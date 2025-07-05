"""Simple script for plotting climate sensor data."""

import os
import sqlite3
import pytz
from datetime import datetime, timedelta
import pytz
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib import dates
from zoneinfo import ZoneInfo

def plotting():
    #Timezones
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
    ax = plt.subplot(3, 1, 1,)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M", tz=ZoneInfo("Europe/Helsinki")))   
    plt.scatter(x=df.time, y=df.co2, s=2)
    plt.ylabel('CO2 (ppm)')

    plt.subplot(3, 1, 2, sharex=ax)
    plt.scatter(x=df.time, y=df.temperature, s=2)
    plt.ylabel('Temp (°C)')

    plt.subplot(3, 1, 3, sharex=ax)
    plt.scatter(x=df.time, y=df.humidity, s=2)
    plt.ylabel('Humidity (RH%)')
    
    plt.suptitle(t_end_local.strftime('Kiltis %d.%m.%Y at %H:%M:%S'), fontsize=20)
    
    os.makedirs('plots', exist_ok=True)
    # Save the figure as a png to a location
    plt.savefig(os.path.join('plots', 'newest.png'))


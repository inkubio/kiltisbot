"""Simple script for plotting climate sensor data."""

import glob
import os.path
import os
import sqlite3
import pytz
from datetime import datetime, timedelta
import pytz
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import dates


def plotting():
    # Set here the desired time range
    #t_start = '2024-09-17 00:00:00'
    #t_end = '2024-09-18 00:00:00'

    # Timerange to be the last 24h
    t_end = datetime.now(pytz.timezone('Europe/Helsinki'))
    t_start = t_end + timedelta(days=-1)

    # Register datetime converter to ensure correct plotting by matplotlib
    pd.plotting.register_matplotlib_converters()
    
    """
    # Find paths to all .csv-files in ./data -folder
    #csv_file_paths = glob.glob(os.path.join('data', '*.csv'))

    # Combine all csv files to a single data frames
    #data_files = []
    #for month_file in csv_file_paths:
    #    df = pd.read_csv(
    #        month_file,
    #        names=(
    #            'unixtime',
    #            'temperature',
    #            'co2',
    #            'humidity'
    #        )
    #    )
    #    data_files.append(df)
    #data = pd.concat(data_files, ignore_index=True)

    # Add human-readable timestamps and correct them for our timezone
    #data['time'] = (pd.to_datetime(data['unixtime'], unit='s')).dt.tz_localize('UTC').dt.tz_convert('Europe/Helsinki')

    # Filter data by selection
    #data = data[(data.time >= t_start) & (data.time <= t_end)]
    """

    conn = sqlite3.connect("climate.db")

    query = """
        SELECT timestamp, temperature, co2, humidity
        FROM climate_data
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    """
    # Format timestamps as string for SQL
    t_start_str = t_start.strftime("%Y-%m-%d %H:%M:%S")
    t_end_str = t_end.strftime("%Y-%m-%d %H:%M:%S")

    df = pd.read_sql_query(query, conn, params=(t_start_str, t_end_str))
    conn.close()

    # Convert timestamp column to datetime and localize
    df['time'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Europe/Helsinki')

    # Plot data and show results
    ax = plt.subplot(3, 1, 1,)
    ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
    plt.scatter(x=df.time, y=df.co2, s=2)
    plt.ylabel('CO2 (ppm)')

    plt.subplot(3, 1, 2, sharex=ax)
    plt.scatter(x=df.time, y=df.temperature, s=2)
    plt.ylabel('Temp (°C)')

    plt.subplot(3, 1, 3, sharex=ax)
    plt.scatter(x=df.time, y=df.humidity, s=2)
    plt.ylabel('Humidity (RH%)')

    helsinki_tz = pytz.timezone('Europe/Helsinki')
    now_hel = datetime.now(helsinki_tz)
    plt.suptitle(now_hel.strftime('Kiltis %d.%m.%Y at %H:%M:%S'), fontsize=20)
    
    os.makedirs('plots', exist_ok=True)
    # Save the figure as a png to a location
    plt.savefig(os.path.join('plots', 'newest.png'))


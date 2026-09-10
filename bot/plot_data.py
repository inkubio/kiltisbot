import os
import sqlite3
from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.ticker import MaxNLocator, AutoMinorLocator


def plotting():
    """
    Draws a climate data plot of the last 24h.
    If no data vailable, the plot will be empty.
    """
    # Timezones
    helsinki_tz = ZoneInfo('Europe/Helsinki')

    # Timerange to be the last 24h (in Helsinki time)
    t_end_local = datetime.now(helsinki_tz)
    t_start_local = t_end_local - timedelta(days=1)

    # Timerange in UTC
    t_end_utc = t_end_local.astimezone(UTC)
    t_start_utc = t_start_local.astimezone(UTC)

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

    if not df.empty:
        duration = df.time.iloc[-1] - df.time.iloc[0]
        hours = duration.total_seconds() / 3600

        if hours < 1:
            title_text = f"{int(duration.total_seconds() // 60)} min"
        elif hours < 24:
            title_text = f"{hours:.1f} h"
        else:
            title_text = f"24 h"
    else:
        title_text = "No data"
        duration = timedelta(hours=24)

    locator = AutoDateLocator(minticks=3, maxticks=10)
    formatter = ConciseDateFormatter(locator)

    # Plot data and show results
    fig, axs = plt.subplots(
        3, 1,
        sharex=True,
    )

    fig.tight_layout()

    fig.suptitle(
        f"Kiltis Climate • Last {title_text}\nUpdated {t_end_local:%d.%m.%Y at %H:%M:%S}",
        fontsize=20
    )

    # Format the shared x-axis and other shared information.
    for ax in axs:

        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.grid(which="major", axis="x", linestyle="-")
        ax.grid(which="minor", axis="x", linestyle="--")

        ax.yaxis.set_major_locator(MaxNLocator(nbins=3, min_n_ticks=2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(n=2))
        ax.grid(which="major", axis="y", linestyle="-")
        ax.grid(which="minor", axis="y", linestyle="--")

    # Format the individual subplots and their axis.

    ax = axs[0]
    ax.plot(df.time, df.co2, color='green', linewidth=0.8)
    ax.set_ylabel('CO2 (ppm)')

    ax = axs[1]
    ax.plot(df.time, df.temperature, color='red', linewidth=0.8)
    ax.set_ylabel('Temp (°C)')

    ax = axs[2]
    ax.plot(df.time, df.humidity, color='blue', linewidth=0.8)
    ax.set_ylabel('Humidity (RH%)')

    os.makedirs('plots', exist_ok=True)
    # Save the figure as a png to a location
    plt.savefig(os.path.join('plots', 'newest.png'))
    plt.close(fig)

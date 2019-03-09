#!/usr/bin/env python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import itertools
import datetime as dt
from matplotlib import ticker
# Map between Meteoswiss icon IDs and ConkyWeather font letters
weathericons = {
    1: "a",
    2: "b",
    3: "c",
    4: "d",
    5: "f",
    6: "g",
    7: "o",
    8: "o",
    9: "g",
    10: "o",
    11: "o",
    12: "k",
    13: "k",
    14: "h",
    15: "p",
    16: "p",
    17: "i",
    18: "p",
    19: "q",
    20: "j",
    21: "q",
    22: "q",
    23: "l",
    24: "m",
    25: "n",
    26: "b",
    27: "9",
    28: "0",
    29: "g",
    30: "o",
    31: "o",
    32: "g",
    33: "g",
    34: "o",
    35: "e",
    101: "A",
    102: "B",
    103: "C",
    104: "D",
    105: "f",
    106: "G",
    107: "O",
    108: "O",
    109: "G",
    110: "O",
    111: "O",
    112: "K",
    113: "K",
    114: "h",
    115: "p",
    116: "p",
    117: "i",
    118: "p",
    119: "q",
    120: "j",
    121: "q",
    122: "q",
    123: "l",
    124: "m",
    125: "n",
    126: "B",
    127: "9",
    128: "0",
    129: "G",
    130: "O",
    131: "O",
    132: "G",
    133: "G",
    134: "O",
    135: "e"
}


# create a time format string from an unix timestamp
def format_time(time, pos=None):
    return dt.datetime.fromtimestamp(time).strftime('%H:%M')


def generate_plot(weather_data):
    j = weather_data

    # Extract the temperatures, precipitations and timestamps for the first two days in the json file.
    temps = [ row[1]           for k in [0, 1] for row in j[k].get("temperature") ]
    precs = [ row[1]           for k in [0, 1] for row in j[k].get("rainfall")    ]
    times = [ int(row[0]/1000) for k in [0, 1] for row in j[k].get("temperature") ]

    # Extract icon information
    icons = [ {"time":row.get("timestamp")/1000, "icon":weathericons[row.get("weather_symbol_id")]} for k in [0,1] for row in j[k].get("symbols") ]

    # current time as reported by json, in seconds
    now = j[0].get("current_time") / 1000

    # timespan to display
    starttime = now - 3600
    endtime = now + 24 * 3600

    # filter the temps, precs and times array such that only values within the timespan are included
    indices = [starttime < x < endtime for x in times]
    temps = list(itertools.compress(temps, indices))
    precs = list(itertools.compress(precs, indices))
    times = list(itertools.compress(times, indices))

    # where ticks on the x axis should go
    xticks = times[2::3]

    # max and min temperature, for adjusting the y axis range
    maxtemp = max(temps)
    mintemp = min(temps)

    # Set up plot
    fig, ax1 = plt.subplots(figsize=(6, 3))
    for tl in ax1.get_xticklabels():
        tl.set_color('w')  # set all x tick labels to white
    ax1.xaxis.set_major_formatter(ticker.FuncFormatter(format_time))  # make the x axis convert unix timestamps to time strings
    ax1.xaxis.set_ticks(xticks)  # set tick interval according to our xticks list
    ax1.spines['top'].set_visible(False)  # remove top border

    # Plot precipitation
    ax1.bar([x-1750 for x in times], precs, 3500, color='#aaaaff')
    ax1.set_ylim([0, 8])  # y axis range hardcoded to 0-8, that's usually fine
    ax1.set_facecolor('k')

    # Set all y tick labels to white (for the precipitation values)
    for tl in ax1.get_yticklabels():
        tl.set_color('w')

    # Plot weather icons
    for icon in icons:
        if starttime < icon["time"] < endtime:
            ax1.text(icon["time"] - 1800, 7.5, icon["icon"], color='w', fontname="ConkyWeather", fontstyle='oblique', fontsize=20)

    # Add new y axis and plot temperature
    ax2 = ax1.twinx()
    ax2.spines['top'].set_visible(False)  # remove top border
    ax2.plot(times, temps, 'w',  linewidth=3)
    ax2.set_ylim([mintemp - 2, maxtemp + 2])  # y axis range
    ax2.vlines(now, mintemp - 2, maxtemp + 1, colors='w', linestyles='dotted')  # verticl line where the current time is

    # set temperature y tick labels to white
    for tl in ax2.get_yticklabels():
        tl.set_color('w')

    # save figure to file
    fig.savefig('/tmp/weather.png', facecolor='k', edgecolor='none', transparent=True, bbox_inches='tight', dpi=100)
    return '/tmp/weather.png'

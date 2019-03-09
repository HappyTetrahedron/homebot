import datetime

from base_handler import *
import logging

logger = logging.getLogger(__name__)

import json
import requests
import re

import weather_plotter

key = "wth"

JSON_PATH_REGEX = re.compile('data-forecast-json-url="(.+)"')

params = {}

METEO_JSON_URL = "https://www.meteoswiss.admin.ch{}"
METEO_PAGE_URL = "https://www.meteoswiss.admin.ch/home.html?tab=overview"


def setup(config, send_message):
    params['config'] = config['weather']


def matches_message(message):
    return "weather" in message.lower()


def handle(message, db):
    result = requests.get(METEO_PAGE_URL, timeout=7)
    match = JSON_PATH_REGEX.search(result.text)
    if not match:
        return "There appears to be an issue with the Meteo page parsing"

    json_path = match.groups()[0]
    json_url = METEO_JSON_URL.format(json_path)

    weather_data = json.loads(requests.get(json_url, timeout=7).text)

    if "tomorrow" in message:
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        tomorrow_morning = datetime.datetime(year=tomorrow.year,
                                             month=tomorrow.month,
                                             day=tomorrow.day,
                                             hour=5)
        starttime = tomorrow_morning.timestamp()
        plot, start, end = weather_plotter.generate_plot(weather_data, starttime)

    else:
        plot, start, end = weather_plotter.generate_plot(weather_data)

    start_time = datetime.datetime.fromtimestamp(start)
    end_time = datetime.datetime.fromtimestamp(end)

    return {
        'message': "Weather from {} to {}".format(
            start_time.strftime("%A, %B %-d at %-H:%M"),
            end_time.strftime("%A, %B %-d at %-H:%M")
        ),
        'photo': plot,
    }


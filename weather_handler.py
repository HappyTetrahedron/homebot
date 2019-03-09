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

    plot = weather_plotter.generate_plot(weather_data)

    return {
        'message': "Weather.",
        'photo': plot,
    }


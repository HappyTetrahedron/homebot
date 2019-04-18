from base_handler import *

import datetime
import logging
import json
import requests
import re

from unicodedata import normalize

import weather_plotter

key = "wth"

logger = logging.getLogger(__name__)

JSON_PATH_REGEX = re.compile('data-forecast-json-url="(.+)"')
VERSION_TIMESTAMP_REGEX = re.compile('data-forecast-json-url=".*/version__(.+?)/.*"')

params = {}

METEO_JSON_URL = "https://www.meteoswiss.admin.ch{}"
METEO_PAGE_URL = "https://www.meteoswiss.admin.ch/home.html?tab=overview"

METEO_FORECAST_URL = "https://www.meteoswiss.admin.ch/product/output/forecast-chart/version__{}/en/{}.json"
METEO_SEARCH_URL = "https://www.meteoswiss.admin.ch/etc/designs/meteoswiss/ajax/search/{}.json"

REFRESH = "ref"

def setup(config, send_message):
    params['config'] = config['weather']


def matches_message(message):
    return "weather" in message.lower()


def handle(message, **kwargs):
    zip = params['config']['zip']
    city_name = params['config']['city']

    words = message.split()
    if "in" in words:
        location_words = words[words.index("in") + 1:]
        if location_words:
            location = " ".join(location_words).lower().strip()
            firstletters = de_unicodize(location)[:2]
            search_results = json.loads(requests.get(METEO_SEARCH_URL.format(firstletters), timeout=7).text)
            cities = []
            for r in search_results:
                parts = r.split(";")
                city = {
                    'zip': parts[0],
                    'canton': parts[1],
                }

                iterator = iter(parts[2:])
                for part in iterator:
                    city[part] = next(iterator)
                cities.append(city)

            matches = []
            for city in cities:
                if '4' in city:
                    if location in city['4'].lower():
                        city['name'] = city['4']
                        matches.append(city)
                if '1' in city:
                    if location in city['1'].lower():
                        city['name'] = city['1']
                        matches.append(city)
            best_match = {}
            shortest_len = 1000
            for city in matches:
                if len(city['name']) < shortest_len:
                    best_match = city
                    shortest_len = len(city['name'])

            if not best_match:
                for city in cities:
                    if '4' in city:
                        if city['4'].lower() in location:
                            city['name'] = city['4']
                            matches.append(city)
                    elif '1' in city:
                        if city['1'].lower() in location:
                            city['name'] = city['1']
                            matches.append(city)
                longest_len = 0
                for city in matches:
                    if len(city['name']) > longest_len:
                        best_match = city
                        longest_len = len(city['name'])

            if best_match:
                zip = best_match['zip']
                city_name = "{} {}".format(best_match['name'], best_match['canton'])

    return get_weather_data(zip, city_name, "tomorrow" in message)


def handle_button(data, **kwargs):
    parts = data.split(":", 1)
    cmd = parts[0]
    parts = parts[1].split(":")

    if cmd == REFRESH:
        msg = get_weather_data(parts[0], parts[1], parts[2].lower() == "true")
        msg['answer'] = "Refreshed!"
        return msg
    return "Oh, something went wrong."


def get_weather_data(zip, city_name, for_tomorrow):
    result = requests.get(METEO_PAGE_URL, timeout=7)
    match = VERSION_TIMESTAMP_REGEX.search(result.text)
    if not match:
        return "There appears to be an issue with the Meteo page parsing"

    version_timestamp = match.groups()[0]

    json_url = METEO_FORECAST_URL.format(version_timestamp, zip)

    weather_data = json.loads(requests.get(json_url, timeout=7).text)

    if for_tomorrow:
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
        'message': "Weather in {} from {} to {}".format(
            city_name,
            start_time.strftime("%A, %B %-d at %-H:%M"),
            end_time.strftime("%A, %B %-d at %-H:%M")
        ),
        'photo': plot,
        'buttons': [[{
            'text': "Refresh",
            'data': "{}:{}:{}:{}:{}".format(REFRESH, zip, city_name, for_tomorrow, datetime.datetime.now().timestamp())
        }]]
    }


def de_unicodize(string):
    return normalize('NFD', string.lower()).encode('ascii', 'ignore').decode('ascii')


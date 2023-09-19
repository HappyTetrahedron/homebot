from base_handler import *

import datetime
import logging
import json
import requests
import re

from unicodedata import normalize

import weather_plotter

logger = logging.getLogger(__name__)

METEO_JSON_URL = "https://www.meteoswiss.admin.ch{}"
METEO_PAGE_URL = "https://www.meteoswiss.admin.ch/home.html?tab=overview"

METEO_VERSIONS_URL = "https://www.meteoswiss.admin.ch/product/output/versions.json"

METEO_FORECAST_URL = "https://www.meteoswiss.admin.ch/product/output/forecast-chart/version__{}/en/{}.json"
METEO_SEARCH_URL = "https://www.meteoswiss.admin.ch/static/product/resources/local-forecast-search/{}.json"

METEO_API_HEADERS = {"referer": "https://www.meteoswiss.admin.ch/home.html?tab=overview"}

METEO_LANGUAGE_CODE = '1'

REFRESH = "ref"


class WeatherHandler(BaseHandler):
    def __init__(self, config, messenger):
        super().__init__(config, messenger, "wth", "Weather Forecast")
        self.config = config['weather']


    def help(self, permission):
        return {
            'summary': "Tells you the weather for the next 24 hours",
            'examples': [
                "Weather",
                "Weather tomorrow",
                "Weather in Appenzell",
            ],
        }


    def matches_message(self, message):
        return "weather" in message.lower()


    def handle(self, message, **kwargs):
        zip = self.config['zip']
        city_name = self.config['city']

        words = message.split()
        if "in" in words:
            location_words = words[words.index("in") + 1:]
            if location_words:
                location = " ".join(location_words).lower().strip()
                firstletters = self.de_unicodize(location)[:2]
                search_results = json.loads(requests.get(
                    METEO_SEARCH_URL.format(firstletters),
                    headers=METEO_API_HEADERS,
                    timeout=7
                ).text)

                cities = []
                for r in search_results:
                    parts = r.split(";")
                    city = {
                        'zip': parts[0],
                        'canton': parts[1],
                        'name': self.find_name(parts),
                    }
                    cities.append(city)

                matches = []
                for city in cities:
                    if location in city['name'].lower():
                        matches.append(city)
                best_match = {}
                shortest_len = 1000
                for city in matches:
                    if len(city['name']) < shortest_len:
                        best_match = city
                        shortest_len = len(city['name'])

                if not best_match:
                    matches = cities
                    longest_len = 0
                    for city in matches:
                        if len(city['name']) > longest_len:
                            best_match = city
                            longest_len = len(city['name'])

                if best_match:
                    zip = best_match['zip']
                    city_name = "{} {}".format(best_match['name'], best_match['canton'])

        return self.get_weather_data(zip, city_name, "tomorrow" in message)


    def find_name(self, meteo_city_parts):
        return meteo_city_parts[meteo_city_parts.index(METEO_LANGUAGE_CODE) + 1]


    def handle_button(self, data, **kwargs):
        parts = data.split(":", 1)
        cmd = parts[0]
        parts = parts[1].split(":")

        if cmd == REFRESH:
            msg = self.get_weather_data(parts[0], parts[1], parts[2].lower() == "true")
            msg['answer'] = "Refreshed!"
            return msg
        return "Oh, something went wrong."


    def get_weather_data(self, zip, city_name, for_tomorrow):
        result = requests.get(METEO_VERSIONS_URL, timeout=7).json()

        version_timestamp = result["forecast-chart"]

        json_url = METEO_FORECAST_URL.format(version_timestamp, zip)

        weather_data = json.loads(requests.get(
            json_url, headers=METEO_API_HEADERS, timeout=7).text)

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


    def de_unicodize(self, string):
        return normalize('NFD', string.lower()).encode('ascii', 'ignore').decode('ascii')


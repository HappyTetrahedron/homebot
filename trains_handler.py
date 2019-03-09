from base_handler import *

import datetime
import logging
import json
import requests
import re

logger = logging.getLogger(__name__)

params = {}

key = 'zvv'

NEXT_REGEX = re.compile('^next\s+(trains?|trams?|bus(?:ses)?|conn(?:ection)?s?)$',
                        flags=re.I)
NEXT_FROM_REGEX = re.compile('^next\s+(trains?|trams?|bus(?:ses)?|conn(?:ection)?s?)\s+from\s+(.+)$',
                        flags=re.I)
NEXT_FROM_TO_REGEX = re.compile('^next\s+(trains?|trams?|bus(?:ses)?|conn(?:ection)?s?)\s+from\s+(.+)\s+to\s+(.+)$',
                        flags=re.I)

STATIONBOARD_URL = "http://transport.opendata.ch/v1/stationboard?id={}&limit=30"
LOCATION_URL = "http://transport.opendata.ch/v1/locations"
CONNECTION_URL = "http://transport.opendata.ch/v1/connections"

TRAM = "T"
BUS = "BUS"
S_BAHN = "S"
INTERREGIO = "IR"
REGIOEXPRESS = "RE"
INTERCITY = "IC"

LIMIT = 5

REFRESH = "ref"


def setup(config, send_message):
    params['config'] = config['trains']


def matches_message(message):
    return NEXT_REGEX.match(message) is not None \
        or NEXT_FROM_REGEX.match(message) is not None


def handle(message, db):
    matches = NEXT_FROM_TO_REGEX.match(message)
    if matches:
        return find_connection(matches)

    matches = NEXT_FROM_REGEX.match(message)
    if matches:
        return find_stationboards(matches)

    matches = NEXT_REGEX.match(message)
    if matches:
        types = keyword_to_type(matches.groups()[0])
        return stationboard_message(params['config']['home_stations'], types or params['config']['home_types'])


def handle_button(data, db):
    parts = data.split(':', 1)
    cmd = parts[0]
    payload = parts[1]

    if cmd == REFRESH:
        more_parts = payload.split(':')
        stations = more_parts[0].split(',')
        types = more_parts[1].split(',') if more_parts[1] else None
        msg = stationboard_message(stations, types)
        msg['answer'] = "Refreshed!"
        return msg


def find_connection(matches):
    groups = matches.groups()
    from_query = groups[1]
    to_query = groups[2]
    connections = json.loads(requests.get(CONNECTION_URL, params={'from': from_query, 'to': to_query}, timeout=7).text)

    next_minute = (datetime.datetime.now() + datetime.timedelta(minutes=1)).timestamp()

    msg = ""
    for connection in connections['connections']:
        if connection['from']['departureTimestamp'] > next_minute:
            msg += "{} to {} -- {} -- _in {}_\n".format(
                connection['from']['station']['name'],
                connection['to']['station']['name'],
                format_duration_string(connection['duration']),
                format_duration_seconds(connection['from']['departureTimestamp'] - next_minute)
            )
            for section in connection['sections']:
                if section['journey']:
                    msg += " {} {}{}  *{}* {}-- {} {}\n".format(
                        datetime.datetime.fromtimestamp(section['departure']['departureTimestamp']).strftime("%-H:%M"),
                        section['journey']['category'],
                        section['journey']['number'],
                        section['departure']['station']['name'],
                        " Gleis {} ".format(section['departure']['platform']) if section['departure']['platform'] else "",
                        section['arrival']['station']['name'],
                        datetime.datetime.fromtimestamp(section['arrival']['arrivalTimestamp']).strftime("%-H:%M"),
                    )
                elif section['walk']:
                    msg += " -- walk to *{}* {}\n".format(
                        section['arrival']['station']['name'],
                        "({})".format(format_duration_seconds(section['walk']['duration']) if section['walk']['duration'] else "")
                    )
            msg += "\n"

    return {
        'message': msg,
        'parse_mode': 'markdown'
    }


def format_duration_seconds(duration):
    duration = int(duration)
    days = duration // 86400
    duration = duration % 86400
    hours = duration // 3600
    duration = duration % 3600
    mins = duration // 60
    return format_duration(days, hours, mins)


def format_duration_string(duration):
    p = duration.split('d')
    days = int(p[0])
    rest = p[1]

    p = rest.split(':')
    hours = int(p[0])
    mins = int(p[1])
    return format_duration(days, hours, mins)


def format_duration(days, hours, mins):
    dur = ""
    if days > 0:
        dur += "{} day{} ".format(days, "s" if days > 1 else "")
    if hours > 0:
        dur += "{} h {} min".format(hours, mins)
    else:
        dur += "{}{}".format(mins, "'" if days == 0 else " min")
    return dur


def find_stationboards(matches):
    groups = matches.groups()
    types = keyword_to_type(groups[0])
    search_queries = re.split(r'\s*,\s*|\s*and\s*', groups[1])

    stations = []
    for query in search_queries:
        locations = json.loads(requests.get(LOCATION_URL, params={'query': query}, timeout=7).text)
        if locations['stations']:
            station = locations['stations'][0]['id']
            if station:
                stations.append(station)

    if not stations:
        return "No stations found by that name :("
    return stationboard_message(stations, types)


def keyword_to_type(keyword):
    if keyword.startswith("tram"):
        return [TRAM]
    if keyword.startswith("bus"):
        return [BUS]
    return None


def stationboard_message(stations, types=None):
    stationboards = []

    for station in stations:
        station_url = STATIONBOARD_URL.format(station)
        stationboard = json.loads(requests.get(station_url, timeout=7).text)
        stationboards.append(stationboard)

    for stationboard in stationboards:
        next_minute = (datetime.datetime.now() + datetime.timedelta(minutes=1)).timestamp()
        stationboard['stationboard'] = [connection for connection in stationboard['stationboard']
                                        if (types is None or connection['category'] in types)
                                        and connection['stop']['departureTimestamp'] > next_minute][:LIMIT]

    message = ""

    now = datetime.datetime.now().timestamp()
    for stationboard in stationboards:
        message += "Connections from {}:\n".format(stationboard['station']['name'])
        for connection in stationboard['stationboard']:
            message += "{} {}   {}'\n".format(
                connection['number'],
                connection['to'],
                int((connection['stop']['departureTimestamp'] - now) // 60)
            )
        message += "\n"

    stations_str = ",".join([str(s) for s in stations])
    types_str = ",".join(types) if types else ""
    return {
        'message': message,
        'buttons': [[{
            'text': "Refresh",
            'data': "{}:{}:{}:{}".format(REFRESH, stations_str, types_str, datetime.datetime.now().timestamp())
        }]]
    }

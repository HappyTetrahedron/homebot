from base_handler import *

import datetime
import logging
import json
import requests
import re

logger = logging.getLogger(__name__)

params = {}

key = 'zvv'

NEXT_REGEX = re.compile('^(?:next\s+)?(trains?|trams?|bus(?:ses)?|conn(?:ection)?s?)$',
                        flags=re.I)
NEXT_FROM_REGEX = re.compile('^(?:next\s+)?(trains?|trams?|bus(?:ses)?|conn(?:ection)?s?)\s+from\s+(.+)$',
                        flags=re.I)
NEXT_FROM_TO_REGEX = re.compile('(?:^next\s+)?(trains?|trams?|bus(?:ses)?|conn(?:ection)?s?)\s+from\s+(.+)\s+to\s+(.+)$',
                        flags=re.I)

STATIONBOARD_URL = "http://transport.opendata.ch/v1/stationboard?id={}&limit=30"
LOCATION_URL = "http://transport.opendata.ch/v1/locations"
CONNECTION_URL = "http://transport.opendata.ch/v1/connections"

TRAM = "T"
BUS = "BUS"
NIEDERFLURBUS = "NFB"
S_BAHN = "S"
INTERREGIO = "IR"
REGIOEXPRESS = "RE"
INTERCITY = "IC"
EUROCITY = "EC"

EMOJI = {
    S_BAHN: u"\U0001F688",
    BUS: u"\U0001F68C",
    NIEDERFLURBUS: u"\U0001F68C",
    INTERREGIO: u"\U0001F683",
    TRAM: u"\U0001F68B",
    REGIOEXPRESS: u"\U0001F683",
    INTERCITY: u"\U0001F684",
    EUROCITY: u"\U0001F685"
}

DEFAULT_EMOJI = u"\U0001F682"

WALK_EMOJI = u"\U0001F9B6\U0001F3FB"

LIMIT = 5

REFRESH_STATIONBOARD = "ref"
REFRESH_CONNECTIONS = "rec"
AUTO_REFRESH_STATIONBOARD = "arc"
AUTO_REFRESH_CONNECTIONS = "ars"
STOP_AUTO_REFRESH = "sar"


def setup(config, send_message):
    params['config'] = config['trains']
    params['sendmsg'] = send_message
    params['debug'] = config['debug']


def matches_message(message):
    return NEXT_REGEX.match(message) is not None \
        or NEXT_FROM_REGEX.match(message) is not None


def handle(message, **kwargs):
    matches = NEXT_FROM_TO_REGEX.match(message)
    if matches:
        groups = matches.groups()
        from_query = groups[1]
        to_query = groups[2]
        return find_connection(from_query, to_query)

    matches = NEXT_FROM_REGEX.match(message)
    if matches:
        return find_stationboards(matches)

    matches = NEXT_REGEX.match(message)
    if matches:
        types = keyword_to_type(matches.groups()[0])
        return stationboard_message(params['config']['home_stations'], types or params['config']['home_types'])


def handle_button(data, **kwargs):
    db = kwargs['db']
    message_id = kwargs['message_id']
    actor_id = kwargs['actor_id']
    parts = data.split(':', 1)
    cmd = parts[0]
    payload = parts[1]

    auto_refreshes = db['train_auto_refresh']

    if cmd == REFRESH_STATIONBOARD:
        more_parts = payload.split(':')
        stations = more_parts[0].split(',')
        types = more_parts[1].split(',') if more_parts[1] else None
        msg = stationboard_message(stations, types)
        msg['answer'] = "Refreshed!"
        return msg
    if cmd == REFRESH_CONNECTIONS:
        more_parts = payload.split(':')
        from_station = more_parts[0]
        to_station = more_parts[1]
        msg = find_connection(from_station, to_station)
        msg['answer'] = "Refreshed!"
        return msg
    if cmd == AUTO_REFRESH_STATIONBOARD:
        more_parts = payload.split(':')
        stations = more_parts[0].split(',')
        types = more_parts[1].split(',') if more_parts[1] else None
        auto_refresh = {
            'message': message_id,
            'stations': ",".join(stations),
            'types': ",".join(types),
            'until': datetime.datetime.now() + datetime.timedelta(minutes=15),
            'actor': actor_id,
        }
        auto_refreshes.insert(auto_refresh)
        msg = stationboard_message(stations, types, stop_auto_refresh=True)
        msg['answer'] = "Auto-refresh enabled!"
        return msg
    if cmd == AUTO_REFRESH_CONNECTIONS:
        more_parts = payload.split(':')
        from_station = more_parts[0]
        to_station = more_parts[1]
        auto_refresh = {
            'message': message_id,
            'from_station': from_station,
            'to_station': to_station,
            'until': datetime.datetime.now() + datetime.timedelta(minutes=15),
            'actor': actor_id,
        }
        auto_refreshes.insert(auto_refresh)
        msg = find_connection(from_station, to_station, stop_auto_refresh=True)
        msg['answer'] = "Auto-refresh enabled!"
        return msg
    if cmd == STOP_AUTO_REFRESH:
        auto_refresh = auto_refreshes.find_one(message=message_id)
        if not auto_refresh:
            return "Oh damn, this shouldn't happen!"
        msg = get_auto_refresh_message(auto_refresh, False)
        auto_refreshes.delete(id=auto_refresh['id'])
        msg['answer'] = "Auto-refresh stopped!"
        return msg

    return "Oh, looks like something went wrong..."


def find_connection(from_query, to_query, stop_auto_refresh=False):
    connections = json.loads(requests.get(CONNECTION_URL, params={'from': from_query, 'to': to_query}, timeout=7).text)

    next_minute = (datetime.datetime.now() + datetime.timedelta(minutes=1)).timestamp()

    from_id = from_query
    to_id = to_query
    msg = ""
    for connection in connections['connections']:
        if connection['from']['departureTimestamp'] > next_minute:
            if 'id' in connection['from']:
                from_id = connection['from']['id']
            if 'id' in connection['to']:
                to_id = connection['to']['id']
            msg += "{} to {} -- {} -- _in {}_\n".format(
                connection['from']['station']['name'],
                connection['to']['station']['name'],
                format_duration_string(connection['duration']),
                format_duration_seconds(connection['from']['departureTimestamp'] - next_minute)
            )
            logger.info("MESSAGE ---- {}".format(msg))
            for section in connection['sections']:
                if section['journey']:
                    msg += "{} {} {}{}  *{}* {} ─ {} {}\n".format(
                        EMOJI[section['journey']['category']]
                        if section['journey']['category'] in EMOJI
                        else DEFAULT_EMOJI,
                        datetime.datetime.fromtimestamp(section['departure']['departureTimestamp']).strftime("%-H:%M"),
                        "" if section['journey']['number'].startswith(section['journey']['category'])
                        else section['journey']['category'],
                        section['journey']['number'],
                        section['departure']['station']['name'],
                        " Gleis {} ".format(section['departure']['platform'])
                        if section['departure']['platform']
                        else "",
                        section['arrival']['station']['name'],
                        datetime.datetime.fromtimestamp(section['arrival']['arrivalTimestamp']).strftime("%-H:%M"),
                    )
                elif section['walk']:
                    msg += "{} walk to *{}* {}\n".format(
                        WALK_EMOJI,
                        section['arrival']['station']['name'],
                        "({})".format(format_duration_seconds(section['walk']['duration']))
                        if section['walk']['duration']
                        else ""
                    )
            msg += "\n"

    if msg == "":
        return "Oh no, there don't seem to be any connections between these stations. Do they really exist?"
    return {
        'message': msg,
        'parse_mode': 'markdown',
        'buttons': [[{
            'text': "Refresh",
            'data': "{}:{}:{}:{}".format(REFRESH_CONNECTIONS, from_id, to_id, next_minute)
        }],
        [{
            'text': "Stop Auto-Refresh" if stop_auto_refresh else "Auto-Refresh",
            'data': "{}:0".format(STOP_AUTO_REFRESH)
            if stop_auto_refresh
            else "{}:{}:{}:{}".format(AUTO_REFRESH_CONNECTIONS, from_id, to_id, next_minute)
        }]]

    }


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


def stationboard_message(stations, types=None, stop_auto_refresh=False):
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
            message += "{} {} {}   {}'\n".format(
                EMOJI[connection['category']] if connection['category'] in EMOJI else DEFAULT_EMOJI,
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
            'data': "{}:{}:{}:{}".format(REFRESH_STATIONBOARD, stations_str, types_str,
                                         datetime.datetime.now().timestamp())
        }],
        [{
            'text': "Stop Auto-Refresh" if stop_auto_refresh else "Auto-Refresh",
            'data': "{}:0".format(STOP_AUTO_REFRESH)
            if stop_auto_refresh
            else "{}:{}:{}:{}".format(AUTO_REFRESH_STATIONBOARD, stations_str, types_str,
                                      datetime.datetime.now().timestamp())
        }]]
    }


def run_periodically(db):
    table = db['train_auto_refresh']
    auto_refreshes = table.all()
    for auto_refresh in auto_refreshes:
        if params['debug']:
            logger.info("Auto-Refreshing message {}".format(auto_refresh['message']))
        continue_refreshing = auto_refresh['until'] > datetime.datetime.now()
        msg = get_auto_refresh_message(auto_refresh, continue_refreshing)
        if not continue_refreshing:
            if params['debug']:
                logger.info("Removing auto-refresh for message {}".format(auto_refresh['message']))
            table.delete(id=auto_refresh['id'])
        params['sendmsg'](msg,
                          update_message_id=auto_refresh['message'],
                          key=key,
                          recipient_id=auto_refresh['actor'] if 'actor' in auto_refresh else None)


def get_auto_refresh_message(auto_refresh, continue_refreshing=True):
    msg = {}
    if 'from_station' in auto_refresh and auto_refresh['from_station'] is not None:
        msg = find_connection(auto_refresh['from_station'], auto_refresh['to_station'],
                              stop_auto_refresh=continue_refreshing)
    elif 'stations' in auto_refresh and auto_refresh['stations'] is not None:
        msg = stationboard_message(auto_refresh['stations'].split(','), auto_refresh['types'].split(','),
                                   stop_auto_refresh=continue_refreshing)
    return msg


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

from base_handler import *

import re
import hue

key = "hue"

TURN_ON_X_PATTERN = re.compile("^turn\s+(on|off)\s+(?:lights?\s+)?(?:in\s+)?(?:the\s+)?(.+?)(?:\s+lights?)?$",
                               flags=re.I)

TURN_X_ON_PATTERN = re.compile("^(?:turn)?\s*(?:lights?\s+in)?\s*(?:the\s+)?(.+?)\s+(on|off)\s*$",
                               flags=re.I)

# Must match this pattern before the others, as it is a subset of the others
IS_X_ON_PATTERN = re.compile("^(is|are)(?:\s+the)?\s+(.+)\s+(on|off)\??\s*$",
                             flags=re.I)

params = {}


def setup(config, send_message):
    params['hue'] = hue.Hue(config['hue'])
    params['rooms'] = config['hue_rooms']


def matches_message(message):
    return IS_X_ON_PATTERN.match(message) \
           or TURN_X_ON_PATTERN.match(message) \
           or TURN_ON_X_PATTERN.match(message)


def handle(message, _):
    match = IS_X_ON_PATTERN.match(message)
    if match:
        return is_on(match)
    match = TURN_ON_X_PATTERN.match(message)
    if match:
        groups = match.groups()
        return turn_onoff(groups[1], groups[0])
    match = TURN_X_ON_PATTERN.match(message)
    if match:
        groups = match.groups()
        return turn_onoff(groups[0], groups[1])


def handle_button(data, _):
    parts = data.split(':')
    msg = turn_onoff(parts[1], parts[0])
    return {
        'answer': msg,
        'message': msg,
    }


def is_on(match):
    groups = match.groups()
    plural = groups[0]
    room = groups[1]
    on = groups[2] == 'on'
    group = get_group_from_room(room)
    if group == -1:
        return "Sorry, I don't know a room named \"{}\"".format(room)
    ison = params['hue'].is_group_on(group)
    affirm = "Yes" if ison == on else "No"
    onoff = "on" if ison else "off"
    msg = "{}, the {} {} {}.".format(affirm, room, plural, onoff)
    button_text = "Turn {} {}!".format("it" if plural == 'is' else "them", "off" if ison else "on")
    return {
        'message': msg,
        'buttons': [[{
            'text': button_text,
            'data': "{}:{}".format('off' if ison else 'on', room.lower())
        }]]
    }


def turn_onoff(room, onoff):
    on = onoff == 'on'
    group = get_group_from_room(room)
    plural = 'are' if room.lower() == 'lights' else 'is'
    if group == -1:
        return "Sorry, I don't know a room named \"{}\"".format(room)
    if on:
        params['hue'].turn_on_group(group)
        return "The {} {} now on.".format(room, plural)
    else:
        params['hue'].turn_off_group(group)
        return "The {} {} now off.".format(room, plural)


def get_group_from_room(room):
    if room in ['light', 'lights']:
        return 0
    room_mapping = params['rooms']
    if room.lower() not in room_mapping:
        return -1
    return room_mapping[room.lower()]


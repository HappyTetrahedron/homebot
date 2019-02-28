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

SET_X_TO_PATTERN = re.compile("^set\s+(?:the\s+)?(.+)\s+to\s+(.+)\.?$",
                              flags=re.I)

COLORS = {
    'red': '#FF0000',
    'green': '#00FF00',
    'blue': '#0000FF',
    'pink': '#FF00FF',
    'magenta': '#FF00FF',
    'yellow': '#FFFF00',
    'cyan': '#00FFFF',
    'aqua': '#00FFFF',
    'chocolate': '#D2691E',
    'coral': '#FF7F50',
    'crimson': '#DC143C',
    'dark blue': '#00008B',
    'dark red': '#8B0000',
    'dark green': '#006400',
    'dark orange': '#FF8C00',
    'dark salmon': '#E9967A',
    'dark violet': '#9400D3',
    'deep pink': '#FF1493',
    'fire brick': '#B22222',
    'forest green': '#228B88',
    'fuchsia': '#FF00FF',
    'gold': '#FFD700',
    'green yellow': '#ADFF2F',
    'hot pink': '#FF69B4',
    'indigo': '4B0082',
    'khaki': '#F0E68C',
    'beekeeper blue': '#00abcf',
    'light blue': '#ADD8E6',
    'light coral': '#F080800',
    'light cyan': '#E0FFFF',
    'light green': '#90EE90',
    'light pink': '#FFB6C1',
    'light salmon': '#FFA07A',
    'lime': '#00FF00',
    'maroon': '#800000',
    'midnight blue': '#191970',
    'navy': '#000080',
    'olive': '#808000',
    'orange': '#FFA500',
    'orange red': '#FF4500',
    'orchid': '#DA70D6',
    'pale green': '#98FB98',
    'pale turquoise': '#AFEEEE',
    'plum': '#DDA0DD',
    'purple': '#800080',
    'rebecca purple': '#663399',
    'royal blue': '#4169E1',
    'salmon': '#FA8072',
    'sea green': '#2E8B57',
    'slate blue': '#6A5ACD',
    'spring green': '#00FF7F',
    'teal': '#008080',
    'tomato': '#FF6347',
    'turquoise': '#40E0D0',
    'violet': '#EE82EE',
    'yellow green': '#9ACD32',
    'white': '#FFFFFF',
}

params = {}


def setup(config, send_message):
    params['hue'] = hue.Hue(config['hue'])
    params['rooms'] = config['hue_rooms']


def matches_message(message):
    return IS_X_ON_PATTERN.match(message) \
           or TURN_X_ON_PATTERN.match(message) \
           or TURN_ON_X_PATTERN.match(message) \
           or SET_X_TO_PATTERN.match(message) \
           or message.lower().startswith("activate ")


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
    match = SET_X_TO_PATTERN.match(message)
    if match:
        return set_to(match)
    if message.lower().startswith("activate "):
        return activate(message[9:])


def handle_button(data, _):
    parts = data.split(':')
    msg = turn_onoff(parts[1], parts[0])
    return {
        'answer': msg,
        'message': msg,
    }


def set_to(match):
    groups = match.groups()
    room = groups[0]
    scene = groups[1]
    hue = params['hue']

    hue_scene = hue.get_scene_info(scene)
    if scene.lower() in COLORS.keys():
        group = get_group_from_room(room)
        if group == -1:
            return "Sorry, I couldn't find a room named \"{}\"".format(room)
        col = COLORS[scene.lower()]
        huecol = hue.rgb_to_huecol(col)
        hue.turn_on_group(group)
        hue.set_group_to_color_hsb(group, huecol)
        return "{} set to {}.".format(room, scene)
    if hue_scene:
        hue.activate_scene(hue_scene['group'], hue_scene['key'])
        return "Scene {} activated.".format(hue_scene['scene'])
    return "Sorry, I don't know what you mean by \"{}\"".format(scene)


def activate(scene):
    hue = params['hue']
    hue_scene = params['hue'].get_scene_info(scene)

    if hue_scene:
        hue.activate_scene(hue_scene['group'], hue_scene['key'])
        return "Scene {} activated.".format(hue_scene['scene'])

    return "I don't know of a scene named \"{}\"".format(scene)


def is_on(match):
    groups = match.groups()
    plural = groups[0].lower()
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


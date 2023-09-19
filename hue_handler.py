from base_handler import *

import re
import hue
import requests
from utils import get_affirmation, PERM_ADMIN

TURN_ON_X_PATTERN = re.compile("^turn\s+(on|off)\s+(?:lights?\s+)?(?:in\s+)?(?:the\s+)?(.+?)(?:\s+lights?)?$",
                               flags=re.I)

TURN_X_ON_PATTERN = re.compile("^(?:turn)?\s*(?:lights?\s+in)?\s*(?:the\s+)?(.+?)\s+(on|off)\s*$",
                               flags=re.I)

# Must match this pattern before the others, as it is a subset of the others
IS_X_ON_PATTERN = re.compile("^(is|are)(?:\s+the)?\s+(.+)\s+(on|off)\??\s*$",
                             flags=re.I)

SET_X_TO_PATTERN = re.compile("^set\s+(?:the\s+)?(.+)\s+to\s+(.+)\.?$",
                              flags=re.I)

TURN_ON = "on"
TURN_OFF = "off"
TRY_AGAIN = "try"

TIMEOUT_MESSAGE = "Oh, looks like I can't reach your Hue bridge :("

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
    'brown': '#D2691E',
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

class HueHandler(BaseHandler):

    def __init__(self, config, messenger):
        super().__init__(config, messenger, "hue", "Light Control")
        if 'hue' in config:
            self.hue = hue.Hue(config['hue'])
            self.rooms = config['hue_rooms']
            self.enabled = True
        else:
            self.enabled = False


    def help(self, permission):
        if not self.enabled:
            return
        if permission >= PERM_ADMIN:
            example_room = next(iter(self.rooms.keys()))
            all_rooms = "Available rooms:\n"
            for room in self.rooms.keys():
                all_rooms += "- {}\n".format(room)
            return {
                'summary': "Controls your Philips Hue lights",
                'examples': ["turn lights on", "turn {} off".format(example_room), "activate <scene>", "set lights to pink"],
                'extended': all_rooms,
            }


    def matches_message(self, message):
        if not self.enabled:
            return False
        return IS_X_ON_PATTERN.match(message) \
               or TURN_X_ON_PATTERN.match(message) \
               or TURN_ON_X_PATTERN.match(message) \
               or SET_X_TO_PATTERN.match(message) \
               or message.lower().startswith("activate ")


    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, I can't mess with the lights for you."
        try:
            match = IS_X_ON_PATTERN.match(message)
            if match:
                return self.is_on(match)
            match = TURN_ON_X_PATTERN.match(message)
            if match:
                groups = match.groups()
                return self.turn_onoff(groups[1], groups[0])
            match = TURN_X_ON_PATTERN.match(message)
            if match:
                groups = match.groups()
                return self.turn_onoff(groups[0], groups[1])
            match = SET_X_TO_PATTERN.match(message)
            if match:
                return self.set_to(match)
            if message.lower().startswith("activate "):
                return self.activate(message[9:])
        except requests.exceptions.ConnectTimeout:
            return {
                'message': TIMEOUT_MESSAGE,
                'buttons': [[{
                    'text': "Try again!",
                    'data': "{}:{}".format(TRY_AGAIN, message)
            }]],
            }


    def handle_button(self, data, **kwargs):
        parts = data.split(':', 2)
        cmd = parts[0]
        if cmd == TRY_AGAIN:
            msg = self.handle(parts[1])
            if msg['message'] == TIMEOUT_MESSAGE:
                return "It still doesn't work"
            msg['answer'] = get_affirmation()
            return msg
        msg = self.turn_onoff(parts[1], parts[0])
        return {
            'answer': msg,
            'message': msg,
        }


    def set_to(self, match):
        groups = match.groups()
        room = groups[0]
        scene = groups[1]
        hue = self.hue

        hue_scene = hue.get_scene_info(scene)
        if scene.lower() in COLORS.keys():
            group = self.get_group_from_room(room)
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


    def activate(self, scene):
        hue = self.hue
        hue_scene = self.hue.get_scene_info(scene)

        if hue_scene:
            hue.activate_scene(hue_scene['group'], hue_scene['key'])
            return "Scene {} activated.".format(hue_scene['scene'])

        return "I don't know of a scene named \"{}\"".format(scene)


    def is_on(self, match):
        groups = match.groups()
        plural = groups[0].lower()
        room = groups[1]
        on = groups[2] == 'on'
        group = self.get_group_from_room(room)
        if group == -1:
            return "Sorry, I don't know a room named \"{}\"".format(room)
        ison = self.hue.is_group_on(group)
        affirm = "Yes" if ison == on else "No"
        onoff = "on" if ison else "off"
        msg = "{}, the {} {} {}.".format(affirm, room, plural, onoff)
        button_text = "Turn {} {}!".format("it" if plural == 'is' else "them", "off" if ison else "on")
        return {
            'message': msg,
            'buttons': [[{
                'text': button_text,
                'data': "{}:{}".format(TURN_OFF if ison else TURN_ON, room.lower())
            }]]
        }


    def turn_onoff(self, room, onoff):
        on = onoff == 'on'
        group = self.get_group_from_room(room)
        plural = 'are' if room.lower() == 'lights' else 'is'
        if group == -1:
            return "Sorry, I don't know a room named \"{}\"".format(room)
        if on:
            self.hue.turn_on_group(group)
            return "The {} {} now on.".format(room, plural)
        else:
            self.hue.turn_off_group(group)
            return "The {} {} now off.".format(room, plural)


    def get_group_from_room(self, room):
        if room in ['light', 'lights']:
            return 0
        room_mapping = self.rooms
        if room.lower() not in room_mapping:
            return -1
        return room_mapping[room.lower()]


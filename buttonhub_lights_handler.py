from requests import HTTPError

from base_handler import *
import requests

from utils import PERM_ADMIN

class ButtonhubLightsHandler(BaseHandler):
    def __init__(self, config, messenger):
        super().__init__(config, messenger, "buttonhub", "Buttonhub")
        self.base_url = None
        self.enabled = False
        if 'buttonhub' in config:
            self.base_url = config['buttonhub']['base_url']
            self.lights = config['buttonhub'].get('lights')
            self.enabled = self.lights and self.base_url

    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Can check which lights are on",
            'examples': ["lights"],
        }


    def matches_message(self, message):
        if not self.enabled:
            return
        return message.lower().strip() == 'lights'


    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        return self.check_lights()


    def check_lights(self):
        rooms = self.lights['rooms']
        default_field = self.lights['default_field']
        default_on_state = self.lights['default_on_state']

        try:
            lights_on_in = []

            buttonhub_state = self._get_state()
            for room in rooms:
                for device in room['devices']:
                    device_name = device['name']
                    is_on = (buttonhub_state.get(device_name) or {}).get(default_field) == default_on_state
                    if is_on:
                        lights_on_in.append(room['name'])
                        break

            if not lights_on_in:
                return 'No lights are on'

            return 'Lights are on in:\n- ' + '\n- '.join(lights_on_in)
        except HTTPError:
            return {
                'message': 'Failed to check lights :/',
                'answer': 'Error!',
            }
        except requests.exceptions.ConnectionError:
            return {
                'message': 'Failed to check lights :/',
                'answer': 'Error!',
            }

    def _get_state(self):
        response = requests.get(f'{self.base_url}/state', timeout=5)
        response.raise_for_status()
        return response.json()

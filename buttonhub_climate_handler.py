from requests import HTTPError

from base_handler import *
import requests

from utils import PERM_ADMIN

UPDATE_LIST = 'up'

class ButtonhubClimateHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="buttonhub_climate", name="Buttonhub Climate")
        self.base_url = None
        self.enabled = False
        if 'buttonhub' in config:
            self.base_url = config['buttonhub']['base_url']
            self.rooms = config['buttonhub'].get('rooms')
            self.enabled = self.rooms and self.base_url

    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Can check the climate in the flat",
            'examples': ["climate"],
        }


    def matches_message(self, message):
        if not self.enabled:
            return
        return message.lower().strip() == 'climate'


    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        return self.check_climate()


    def check_climate(self):
        try:
            room_states = []

            buttonhub_state = self._get_state()
            for room in self.rooms:
                room_state = []
                for device in room.get('sensors', []):
                    device_name = device['name']
                    device_state = (buttonhub_state.get(device_name) or {})
                    temperature = device_state.get('temperature')
                    if temperature is not None:
                        room_state.append(f'- Temperature: {round(temperature, 1)}°C')
                    humidity = device_state.get('humidity')
                    if humidity is not None:
                        room_state.append(f'- Humidity: {round(humidity, 1)}%')
                    pm25 = device_state.get('pm25')
                    if pm25 is not None:
                        room_state.append(f'- PM2.5: {pm25}')
                if room_state:
                    room_states.append(room['name'] + ':\n' + ('\n'.join(room_state)))

            if not room_states:
                message = 'No sensor readings found'
            else:
                message = '\n\n'.join(room_states)
            return {
                'message': message,
                'buttons': [
                    [
                        {
                            'text': 'Update',
                            'data': UPDATE_LIST,
                        }
                    ]
                ],
            }
        except HTTPError:
            return {
                'message': 'Failed to check climate :/',
                'answer': 'Error!',
            }
        except requests.exceptions.ConnectionError:
            return {
                'message': 'Failed to check climate :/',
                'answer': 'Error!',
            }

    def _get_state(self):
        response = requests.get(f'{self.base_url}/state', timeout=5)
        response.raise_for_status()
        return response.json()

    def handle_button(self, data, **kwargs):
        if data == UPDATE_LIST:
            msg = self.check_climate()
            msg['answer'] = "Updated."
            return msg
        return "Uh oh, something is off"

from base_handler import *
from buttonhub_service import ButtonhubError

from utils import PERM_ADMIN


UPDATE_LIST = 'up'

class ButtonhubLightsHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="buttonhub_lights", name="Buttonhub Lights")
        self.buttonhub_service = service_hub.buttonhub
        self.enabled = False
        if self.buttonhub_service.enabled:
            self.lights = self.buttonhub_service.get_config('lights')
            self.rooms = self.buttonhub_service.get_config('rooms')
            self.enabled = self.lights and self.rooms

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
        default_field = self.lights['default_field']
        default_on_state = self.lights['default_on_state']

        try:
            lights_on_in = []

            buttonhub_state = self.buttonhub_service.get_state()
            for room in self.rooms:
                for device in room['lights']:
                    device_name = device['name']
                    is_on = (buttonhub_state.get(device_name) or {}).get(default_field) == default_on_state
                    if is_on:
                        lights_on_in.append(room['name'])
                        break

            if not lights_on_in:
                message = 'No lights are on'
            else:
                message = 'Lights are on in:\n- ' + '\n- '.join(lights_on_in)
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
        except ButtonhubError:
            return {
                'message': 'Failed to check lights :/',
                'answer': 'Error!',
            }

    def handle_button(self, data, **kwargs):
        if data == UPDATE_LIST:
            msg = self.check_lights()
            msg['answer'] = "Updated."
            return msg
        return "Uh oh, something is off"

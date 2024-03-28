from requests import HTTPError

from base_handler import *
import requests

from utils import PERM_ADMIN

class ButtonhubBatteryHandler(BaseHandler):
    def __init__(self, config, messenger):
        super().__init__(config, messenger, "buttonhub_battery", "Buttonhub Batteries")
        if 'buttonhub' in config:
            self.base_url = config['buttonhub']['base_url']
            self.enabled = True
        else:
            self.base_url = None
            self.enabled = False

    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Can check the battery status of devices connected to Buttonhub",
            'examples': ["batteries"],
        }


    def matches_message(self, message):
        if not self.enabled:
            return
        return message.lower().strip() == 'batteries'


    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        return self.check_batteries()


    def check_batteries(self):
        try:
            battery_status = []

            buttonhub_state = self._get_state()
            for device, value in buttonhub_state.items():
                battery = value.get('battery')
                if battery:
                    battery_status.append(
                        {'device': device.replace('zigbee2mqtt/', ''), 'battery': battery}
                    )

            buttonhub_status = self._get_status()
            for device, value in buttonhub_status.get('devices', {}).items():
                battery = value.get('battery')
                if battery:
                    battery_status.append(
                        {'device': device, 'battery': battery}
                    )

            if not battery_status:
                return 'No devices found'

            return '\n'.join([
                '{}: {}%'.format(s['device'], s['battery'])
                for s in battery_status
            ])
        except HTTPError:
            return {
                'message': 'Failed to check batteries :/',
                'answer': 'Error!',
            }
        except requests.exceptions.ConnectionError:
            return {
                'message': 'Failed to check batteries :/',
                'answer': 'Error!',
            }

    def _get_state(self):
        response = requests.get(f'{self.base_url}/state', timeout=5)
        response.raise_for_status()
        return response.json()

    def _get_status(self):
        response = requests.get(f'{self.base_url}/status', timeout=5)
        response.raise_for_status()
        return response.json()

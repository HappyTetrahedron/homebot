from base_handler import *
import datetime

from buttonhub_service import ButtonhubError
from utils import PERM_ADMIN

UPDATE_LIST = 'up'

class ButtonhubBatteryHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="buttonhub_battery", name="Buttonhub Batteries")
        self.buttonhub_service = service_hub.buttonhub
        self.enabled = False
        if self.buttonhub_service:
            self.config = self.buttonhub_service.config.get('batteries')
            self.enabled = self.config

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
            battery_status = self._get_battery_status()

            if not battery_status:
                message = 'No devices found'
            else:
                message = '\n'.join([
                    '{}: {}%'.format(s['device'], s['battery'])
                    for s in battery_status
                ])
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
                'message': 'Failed to check batteries :/',
                'answer': 'Error!',
            }

    def _get_battery_status(self):
        battery_status = []

        buttonhub_state = self.buttonhub_service.get_state()
        for device, value in buttonhub_state.items():
            battery = value.get('battery')
            if battery:
                device_name = device
                if '/' in device_name:
                    device_name = device_name.split('/')[1]
                battery_status.append(
                    {'device': device_name, 'battery': int(battery)}
                )

        battery_status.sort(key=lambda entry: entry['device'])

        return battery_status

    def handle_button(self, data, **kwargs):
        if data == UPDATE_LIST:
            msg = self.check_batteries()
            msg['answer'] = "Updated."
            return msg
        return "Uh oh, something is off"

    def run_periodically(self, db):
        if not self.enabled:
            return
        now = datetime.datetime.now()
        if now.hour != self.config['hour'] or now.minute != 0:
            return

        threshold = self.config['warning_threshold']

        battery_status = self._get_battery_status()
        endangered_devices = [
            device for device in battery_status if device['battery'] <= threshold
        ]
        if not endangered_devices:
            return

        send = self._messenger.send_message
        if len(endangered_devices) == 1:
            device = endangered_devices[0]
            message = "{} is low on battery ({}%)".format(device['device'], device['battery'])
        else:
            message = "There are devices low on battery:"
            for device in endangered_devices:
                message = message + "\n- {} ({}%)".format(device['device'], device['battery'])
        for user in self.config['users']:
            send(message, recipient_id=user)

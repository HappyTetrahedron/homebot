from base_handler import *
from buttonhub_service import ButtonhubError

from utils import PERM_ADMIN


class ButtonhubModesHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="buttonhub_modes", name="Buttonhub Modes")
        self.buttonhub_service = service_hub.buttonhub
        self.enabled = False
        if self.buttonhub_service.enabled:
            self.modes = self.buttonhub_service.get_config('modes')
            self.enabled = bool(self.modes)

    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Can check which modes are on and such",
            'examples': ["modes"],
        }

    def matches_message(self, message):
        if not self.enabled:
            return
        return message.lower().strip() == 'modes'

    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        return self.check_modes()

    def check_modes(self):
        try:
            result = []
            buttonhub_state = self.buttonhub_service.get_state()
            for mode in self.modes:
                type = mode.get('type')
                display_name = mode.get('display_name')
                topic = mode.get('topic') or ''
                path = mode.get('path') or ''
                value = (buttonhub_state.get(topic) or {}).get(path)
                if type == 'boolean':
                    if value:
                        result.append(f'{display_name}: ON')
                elif type == 'enum':
                    values = (mode.get('values') or [])
                    for possible_value in values:
                        if value == possible_value.get('name'):
                            result.append(f'{display_name}: {possible_value.get('display_name')}')
                            break
            if result:
                message = '\n- '+('\n- '.join(result))
            else:
                message = 'No modes are active'
            return {
                'message': message,
            }
        except ButtonhubError:
            return {
                'message': 'Failed to check modes :/',
                'answer': 'Error!',
            }

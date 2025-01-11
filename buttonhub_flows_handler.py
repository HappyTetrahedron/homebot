from base_handler import *
import re

from buttonhub_service import ButtonhubError
from utils import PERM_ADMIN
from utils import get_affirmation

RUN_FLOW_REGEX = re.compile('^(?:run )?flow ([a-z0-9-]+)', flags=re.I)
TRIGGER_FLOW = 'tr'
SELECT_GROUP = 'sg'
CANCEL = 'cancel'

class ButtonhubFlowsHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="buttonhub_flows", name="Buttonhub Flows")
        self.buttonhub_service = service_hub.buttonhub
        self.enabled = self.buttonhub_service.enabled

    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Can run flows on buttonhub",
            'examples': ["Run flow fish-lamps-on", "flow"],
        }

    def matches_message(self, message):
        if not self.enabled:
            return
        m = message.lower().strip()
        return RUN_FLOW_REGEX.match(message) is not None or m == 'flow' or m == 'flows' or m.startswith('flows ')

    def handle(self, message, **kwargs):
        m = message.lower().strip()
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        if m == 'flows':
            return self.prompt_flow_groups()
        if m.startswith('flows '):
            group_name = m.split(' ')[1]
            return self.prompt_flows(group_name)
        if m == 'flow':
            return self.prompt_flows()
        match = RUN_FLOW_REGEX.match(message)
        flow_name = match.groups()[0]
        return self.trigger_flow(flow_name)

    def handle_button(self, data, **kwargs):
        parts = data.split(':')
        cmd = parts[0]

        if cmd == CANCEL:
            return {
                'message': 'Flow request cancelled',
                'answer': 'Cancelled',
            }
        if cmd == TRIGGER_FLOW:
            return self.trigger_flow(parts[1])
        if cmd == SELECT_GROUP:
            return self.prompt_flows(parts[1])

        return "Uh oh, something is off"

    def trigger_flow(self, flow_name):
        try:
            self.buttonhub_service.run_flow(flow_name)
            return {
                'message': 'Flow {} triggered'.format(flow_name),
                'answer': get_affirmation(),
            }
        except ButtonhubError:
            return {
                'message': 'Failed to trigger flow :/',
                'answer': 'Error!',
            }

    def prompt_flow_groups(self):
        try:
            flows = self.buttonhub_service.get_flows()
            buttons = []
            groups = []
            for flow in flows:
                if flow['hidden']:
                    continue
                group = flow['group']
                if group not in groups:
                    groups.append(group)
            for group in groups:
                buttons.append([{
                    'text': group,
                    'data': '{}:{}'.format(SELECT_GROUP, group)
                }])
            buttons.append([{
                'text': 'Cancel',
                'data': CANCEL,
            }])
            return {
                'message': "Select a group:",
                'buttons': buttons,
            }
        except ButtonhubError:
            return {
                'message': 'Failed to get flows :/',
            }

    def prompt_flows(self, group_prefix=None):
        try:
            flows = self.buttonhub_service.get_flows()
            buttons = []
            for flow in flows:
                if flow['hidden']:
                    continue
                if group_prefix and not flow['group'].startswith(group_prefix):
                    continue
                buttons.append([{
                    'text': flow['label'],
                    'data': '{}:{}'.format(TRIGGER_FLOW, flow['name'])
                }])
            buttons.append([{
                'text': 'Cancel',
                'data': CANCEL,
            }])
            return {
                'message': "Which flow would you like to trigger?",
                'buttons': buttons,
            }
        except ButtonhubError:
            return {
                'message': 'Failed to get flows :/',
            }

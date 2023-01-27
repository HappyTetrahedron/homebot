from requests import HTTPError

from base_handler import *
import re
import requests

from utils import PERM_ADMIN
from utils import get_affirmation

key = "buttonhub"
name = "Buttonhub"

RUN_FLOW_REGEX = re.compile('^(?:run )?flow ([a-z0-9-]+)', flags=re.I)
TRIGGER_FLOW = 'tr'

params = {}


def help(permission):
    if not params['enabled']:
        return
    if permission < PERM_ADMIN:
        return
    return {
        'summary': "Can run flows on buttonhub",
        'examples': ["Run flow fish-lamps-on", "flow"],
    }


def setup(config, send_message):
    if 'buttonhub' in config:
        params['base_url'] = config['buttonhub']['base_url']
        params['enabled'] = True
    else:
        params['enabled'] = False


def matches_message(message):
    if not params['enabled']:
        return
    return RUN_FLOW_REGEX.match(message) is not None or message.lower().strip() == 'flow'


def handle(message, **kwargs):
    if kwargs['permission'] < PERM_ADMIN:
        return "Sorry, you can't do this."
    if message.lower().strip() == 'flow':
        return prompt_flows()
    match = RUN_FLOW_REGEX.match(message)
    flow_name = match.groups()[0]
    return trigger_flow(flow_name)


def handle_button(data, **kwargs):
    parts = data.split('::')
    cmd = parts[0]

    if cmd == TRIGGER_FLOW:
        return trigger_flow(parts[1], parts[2])

    return "Uh oh, something is off"


def trigger_flow(flow_name, flow_label):
    url = '{}/flows/{}'.format(params['base_url'], flow_name)
    try:
        response = requests.post(url, timeout=5)
        response.raise_for_status()
        return {
            'message': 'Flow "{}" triggered'.format(flow_label),
            'answer': get_affirmation(),
        }
    except HTTPError as e:
        return {
            'message': 'Failed to trigger flow: {}'.format(e),
            'answer': 'Error!',
        }
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Failed to trigger flow',
            'answer': 'Error!',
        }


def prompt_flows():
    url = '{}/flows'.format(params['base_url'])
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        flows = response.json()['flows']
        buttons = []
        for flow in flows:
            if flow['hidden']:
                continue
            buttons.append([{
                'text': flow['label'],
                'data': '{}::{}::{}'.format(TRIGGER_FLOW, flow['name'], flow['label'])
            }])
        return {
            'message': "Which flow would you like to trigger?",
            'buttons': buttons,
        }
    except HTTPError as e:
        return {
            'message': 'Failed to get flows: {}'.format(e),
        }
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Failed to get flows',
        }


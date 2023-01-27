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
SELECT_GROUP = 'sg'
CANCEL = 'cancel'

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
    return RUN_FLOW_REGEX.match(message) is not None or message.lower().strip() in ['flow', 'flows']


def handle(message, **kwargs):
    if kwargs['permission'] < PERM_ADMIN:
        return "Sorry, you can't do this."
    if message.lower().strip() == 'flows':
        return prompt_flow_groups()
    if message.lower().strip() == 'flow':
        return prompt_flows()
    match = RUN_FLOW_REGEX.match(message)
    flow_name = match.groups()[0]
    return trigger_flow(flow_name)


def handle_button(data, **kwargs):
    parts = data.split(':')
    cmd = parts[0]

    if cmd == CANCEL:
        return {
            'message': 'Flow request cancelled',
            'answer': 'Cancelled',
        }
    if cmd == TRIGGER_FLOW:
        return trigger_flow(parts[1])
    if cmd == SELECT_GROUP:
        return prompt_flows(parts[1])

    return "Uh oh, something is off"


def trigger_flow(flow_name):
    try:
        _run_flow(flow_name)
        return {
            'message': 'Flow {} triggered'.format(flow_name),
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


def prompt_flow_groups():
    try:
        flows = _get_flows()
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
    except HTTPError as e:
        return {
            'message': 'Failed to get flows: {}'.format(e),
        }
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Failed to get flows',
        }


def prompt_flows(group=None):
    try:
        flows = _get_flows()
        buttons = []
        for flow in flows:
            if flow['hidden']:
                continue
            if group and flow['group'] != group:
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
    except HTTPError as e:
        return {
            'message': 'Failed to get flows: {}'.format(e),
        }
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Failed to get flows',
        }


def _run_flow(flow_name):
    url = '{}/flows/{}'.format(params['base_url'], flow_name)
    response = requests.post(url, timeout=5)
    response.raise_for_status()


def _get_flows():
    url = '{}/flows'.format(params['base_url'])
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()['flows']

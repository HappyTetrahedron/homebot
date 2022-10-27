from requests import HTTPError

from base_handler import *
import re
import requests

from utils import PERM_ADMIN

key = "buttonhub"
name = "Buttonhub"

RUN_FLOW_REGEX = re.compile('^(?:run )?flow ([a-z0-9-]+)', flags=re.I)

params = {}


def help(permission):
    if not params['enabled']:
        return
    if permission < PERM_ADMIN:
        return
    return {
        'summary': "Can run flows on buttonhub",
        'examples': ["Run flow fish-lamps-on"],
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
    return RUN_FLOW_REGEX.match(message) is not None


def handle(message, **kwargs):
    if kwargs['permission'] < PERM_ADMIN:
        return "Sorry, you can't do this."
    match = RUN_FLOW_REGEX.match(message)
    flow_name = match.groups()[0]
    url = '{}/flows/{}'.format(params['base_url'], flow_name)
    try:
        response = requests.post(url, timeout=5)
        response.raise_for_status()
        return {
            'message': 'Flow triggered',
        }
    except HTTPError as e:
        return {
            'message': 'Failed to trigger flow: {}'.format(e),
        }
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Failed to trigger flow',
        }

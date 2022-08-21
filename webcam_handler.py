from base_handler import *
import requests
from utils import PERM_ADMIN
from utils import get_exclamation


key = "webcam"
name = "Webcams"

params = {}

UPDATE = 'UP'
NOIMAGE = 'noimage.png'

def matches_message(message):
    if not params['enabled']:
        return False
    if message.lower().startswith('show '):
        l = message[5:].lower()
        return any([any([l.startswith(prefix) for prefix in x['prefices']])
                    for x in params['cams']])



def help(permission):
    if not params['enabled']:
        return
    if permission >= PERM_OWNER:
        return {
            'summary': "Shows you snapshots from your webcam feeds",
            'examples': ["show living room"],
        }


def setup(config, send_message):
    if 'webcam' in config:
        params['cams'] = config['webcam'].get('cams', [])
        params['tmp_path'] = config['webcam'].get('tmp_path', '/tmp/campic')
        params['enabled'] = True
    else:
        params['enabled'] = False


def handle(message, **kwargs):
    l = message[5:].lower()
    for cam in params['cams']:
        for prefix in cam['prefices']:
            if l.startswith(prefix):
                if ('users' in cam and str(kwargs['actor_id']) in cam['users']) \
                    or ('users' not in cam and kwargs['permission'] >= PERM_ADMIN):
                    return get_snapshot(cam['name'])
                else:
                    return "Sorry, you don't get to see this camera."
    return "Whoopsie, this never happens"


def handle_button(data, **kwargs):
    data = data.split('§', 1)
    cmd = data[0]

    if cmd == UPDATE:
        resp = get_snapshot(data[1])
        resp['answer'] = "Updated!"
        return resp


def get_snapshot(cam):
    buttons = [[{
            'text': "Update",
            'data': "{}§{}".format(UPDATE, cam)
        }]]
    try:
        url = next(c['url'] for c in params['cams'] if c['name'] == cam)
        resp = requests.get(url, timeout=3)
        with open(params['tmp_path'], 'wb') as file:
            file.write(resp.content)
        
        return {
            'message': "{} camera".format(cam),
            'photo': params['tmp_path'],
            'buttons': buttons,
        }
    except requests.exceptions.ConnectionError:
        return {
            'photo': NOIMAGE,
            'message': "{} Seems like the {} webcam isn't online. :(".format(get_exclamation(), cam),
            'buttons': buttons,
        }
    except StopIteration:
        return {
            'photo': NOIMAGE,
            'message': "{} Seems like this webcam doesn't exist anymore. :(".format(get_exclamation()),
        }



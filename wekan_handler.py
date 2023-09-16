from base_handler import *
import requests
from dateutil import parser
from utils import PERM_ADMIN
from utils import get_exclamation


key = "wekan"
name = "wekan"

params = {}

MARK_DONE = 'md'
REMOVE_BUTTONS = 'rm'

def matches_message(message):
    if not params['enabled']:
        return False
    if message.lower() == 'cards':
        return true
    return message.lower().endswith(' cards')


def help(permission):
    if not params['enabled']:
        return
    if permission >= PERM_ADMIN:
        return {
            'summary': "Shows you an overview of your wekan board cards.",
            'examples': ["my cards"],
        }


def setup(config, send_message):
    if 'wekan' in config:
        params['config'] = config['wekan']
        params['enabled'] = True
    else:
        params['enabled'] = False


def handle(message, **kwargs):
    if message.lower() == 'cards':
        lanes = [l['id'] for l in params['config']['lanes']]
    else:
        l = message[:-6].lower()
        lanes = []
        for lane in params['config']['lanes']:
            for name in lane['names']:
                if name in l:
                    lanes.append(lane['id'])
    
    cards = get_my_cards(kwargs['actor_id'], lanes)
    if isinstance(cards, str): # error case
        return cards

    buttons = []
    for card in cards:
        buttons.append([{
            'text': card['title'],
            'data': '{}:{}'.format(MARK_DONE, card['id'])
        }])
    buttons.append([{
            'text': "I'm done",
            'data': REMOVE_BUTTONS
    }])

def card_to_shorthand(card, list):
    list_id = str(params['config']['source_columns'].index(list))
    return '{}.{}'.format(list_id, card)

def shorthand_to_card(shorthand):
    parts = shorthand.split('.', 1)
    list_id = int(parts[0])
    card = parts[1]
    listt = params['config']['source_columns'][list_id]
    return card, listt

def handle_button(data, **kwargs):
    data = data.split(':', 1)
    cmd = data[0]

    if cmd == REMOVE_BUTTONS:
        lanes = data[1].split(',')
        resp = {}
        resp['answer'] = get_affirmation()
        resp['message'] = get_card_text(kwargs['actor_id'], lanes)
        return resp

    if cmd == MARK_DONE:
        args = data[1].split(':')
        lanes = args[1].split(',')
        card_shorthand = args[0]
        card_id, list_id = shorthand_to_card(card_shorthand)

        payload = {
            'listId': params['config']['target_column']
        }

        call_api('/boards/{}/lists/{}/cards/{}'.format(params['config']['board'], list_id, card_id), payload, method=PUT)

        resp = get_card_buttons(kwargs['actor_id'], lanes)
        if isinstance(resp, str):
            return {
                'message': resp,
                'answer': get_affirmation(),
            }

        resp['answer'] = get_affirmation()
        return resp

def get_my_cards(telegram_user, lanes):
    wekan_user = [ u for u in params['config']['users'] if u['telegram_id'] == telegram_user ]

    if len(wekan_user) != 1:
        return "{} I couldn't associate you with a wekan user.".format(get_exclamation())
    wekan_user = wekan_user[0]['wekan_id']

    cards = {}
    for col in params['config']['source_columns']:
        listcards = call_api("boards/{}/lists/{}/cards".format(params['config']['board'], col))
        listcards = [c for c in listcards if len(c['assignees']) == 0 or wekan_user in c['assignees']]
        cards[col] = listcards
    
    if len(cards) == 0:
        return "{}! You've got no cards right now.".format(get_affirmation())

def get_card_text(telegram_uer, lanes):
    cards = get_my_cards(telegram_user, lanes)
    if isinstance(cards, str):
        return cards

    msg = '\n'.join([ '\n'.join([c['title'] for c in subcards]) for subcards in cards.values() ])
    return msg

def get_card_buttons(telegram_user, lanes):
    cards = get_my_cards(telegram_user, lanes)
    if isinstance(cards, str):
        return cards
    buttons = []
    for col, cardlist in cards.items():
        for card in cards:
            buttons.append([{
                'text': card['title'],
                'data': '{}:{}:{}'.format(MARK_DONE, card_to_shorthand(card['_id'], col), ','.join(lanes))
            }])
    buttons.append([{
            'text': "I'm done.",
            'data': '{}:{}'.format(REMOVE_BUTTONS, ','.join(lanes))
    }])

    return {
        'message': "I found the following cards:",
        'buttons': buttons,
    }


def call_api(path, payload=None, method='GET'):
    base_url = params['config']['url']
    if not token_valid():
        login()
    headers = {
        'Authorization': 'Bearer {}'.format(params['token']),
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    if payload:
        if method == 'GET':
            method = 'POST'
        data = requests.request("{}/api/{}".format(base_url, path), method=method, data=payload, headers=headers).json()
    else:
        data = requests.get("{}/api/{}".format(base_url, path), headers=headers).json()
    return data


def token_valid(): 
    return 'token_expires' in params and params['token_expires'] > datetime.datetime.now().astimezone()


def login():
    base_url = params['config']['url']
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    login = {
        'username': params['config']['username'],
        'password': params['config']['password'],
    }
    auth = requests.get("{}/users/login".format(base_url), headers=headers, data=login)
    print(auth.content)
    params['token'] = auth['token']
    params['token_expires'] = parser.parse(auth['tokenExpires'])
    params['wekan_id'] = auth['id']
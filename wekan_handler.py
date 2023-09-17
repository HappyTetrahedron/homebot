from base_handler import *
import requests
from dateutil import parser
import datetime
from utils import PERM_ADMIN
from utils import get_exclamation
from utils import get_affirmation


key = "wekan"
name = "wekan"

params = {}

MARK_DONE = 'md'
DISMISS_LIST = 'rm'
REMOVE_BUTTONS = 'rd'
UPDATE = 'up'
ASSIGN = 'ass'

def matches_message(message):
    if not params['enabled']:
        return False
    if message.lower() == 'cards':
        return True
    if message.lower().endswith(' cards'):
        return True
    if message.lower().startswith('do '):
        return True
    return False


def help(permission):
    if not params['enabled']:
        return
    if permission >= PERM_ADMIN:
        return {
            'summary': "Shows you an overview of your wekan board cards.",
            'examples': [
                "cards",
                "{} cards".format(params['config']['source_lists'][0]['names'][0]),
                "{} cards".format(params['config']['lanes'][0]['names'][0]),
                "do this very important task",
                ],
        }


def setup(config, send_message):
    if 'wekan' in config:
        params['config'] = config['wekan']
        params['enabled'] = True
    else:
        params['enabled'] = False


def handle(message, **kwargs):
    if message.lower() == 'cards':
        message = ' cards'
    if message.lower().startswith('do '):
        task = message[3:]
        return create_card(kwargs['actor_id'], task)
    elif message.lower().endswith(' cards'):
        l = message[:-6].lower()
        lanes = []
        for lane in params['config']['lanes']:
            for name in lane['names']:
                if name in l:
                    lanes.append(lane['id'])
        lists = []
        for list_ in params['config']['source_lists']:
            for name in list_['names']:
                if name in l:
                    lists.append(list_['id'])
        if not lanes and not lists:
            lanes = [l['id'] for l in params['config']['lanes']]
            lists = [l['id'] for l in params['config']['source_lists']]
    
        return get_card_buttons(kwargs['actor_id'], lists, lanes)


def handle_button(data, **kwargs):
    data = data.split(':', 1)
    cmd = data[0]

    if cmd == REMOVE_BUTTONS:
        return {
            'message': "{}! I created the new task for you.".format(get_affirmation()),
            'answer': get_affirmation(),
        }
    if cmd == DISMISS_LIST:
        args = data[1].split(':')
        lists = shorthand_to_lists(args[0].split(','))
        lanes = shorthand_to_lanes(args[1].split(','))
        resp = {}
        resp['answer'] = get_affirmation()
        resp['message'] = get_card_text(kwargs['actor_id'], lists, lanes)
        return resp

    if cmd == UPDATE:
        args = data[1].split(':')
        lists = shorthand_to_lists(args[0].split(','))
        lanes = shorthand_to_lanes(args[1].split(','))
        resp = get_card_buttons(kwargs['actor_id'], lists, lanes)
        resp['answer'] = get_affirmation()
        return resp

    if cmd == MARK_DONE:
        args = data[1].split(':')
        lists = shorthand_to_lists(args[1].split(','))
        lanes = shorthand_to_lanes(args[2].split(','))
        card_shorthand = args[0]
        card_id, list_id = shorthand_to_card(card_shorthand)

        payload = {
            'listId': params['config']['target_list']
        }

        call_api('boards/{}/lists/{}/cards/{}'.format(params['config']['board'], list_id, card_id), payload, method='PUT')

        resp = get_card_buttons(kwargs['actor_id'], lists, lanes)
        if isinstance(resp, str):
            return {
                'message': resp,
                'answer': get_affirmation(),
            }

        resp['answer'] = get_affirmation()
        return resp
    
    if cmd == ASSIGN:
        args = data[1].split(':')
        user_id = args[0]
        user = [ u for u in params['config']['users'] if u['wekan_id'] == user_id ]
        if len(user) < 1:
            user = {}
        else:
            user = user[0]
        card_id, list_id = shorthand_to_card(args[1])
        data = {
            '_id': card_id,
            'assignees': [user_id],
        }
        r = call_api('boards/{}/lists/{}/cards/{}'.format(params['config']['board'], list_id, card_id), data, method='PUT')
        return {
            'message': "{}! I created the new task for you and assigned it to {}.".format(get_affirmation(), user.get('name', '... someone')),
            'answer': get_affirmation(),
        }



def get_card_text(telegram_user, lists, lanes):
    cards = get_my_cards(telegram_user, lists, lanes)
    if isinstance(cards, str):
        return cards

    msg = '\n'.join([ '\n'.join([c['title'] for c in subcards]) for subcards in cards.values() ])
    return msg

def get_card_buttons(telegram_user, lists, lanes):
    cards = get_my_cards(telegram_user, lists, lanes)
    if isinstance(cards, str):
        return cards
    buttons = []
    for li, cardlist in cards.items():
        for card in cardlist:
            buttons.append([{
                'text': card['title'],
                'data': '{}:{}:{}:{}'.format(MARK_DONE, card_to_shorthand(card['_id'], li), ','.join(lists_to_shorthand(lists)), ','.join(lanes_to_shorthand(lanes)))
            }])
    buttons.append([{
            'text': "Update",
            'data': '{}:{}:{}'.format(UPDATE, ','.join(lists_to_shorthand(lists)), ','.join(lanes_to_shorthand(lanes)))
    }])
    buttons.append([{
            'text': "I'm done.",
            'data': '{}:{}:{}'.format(DISMISS_LIST, ','.join(lists_to_shorthand(lists)), ','.join(lanes_to_shorthand(lanes)))
    }])

    return {
        'message': "I found the following cards:",
        'buttons': buttons,
    }


def get_my_cards(telegram_user, lists, lanes):
    wekan_user = [ u for u in params['config']['users'] if u['telegram_id'] == telegram_user ]

    if len(wekan_user) != 1:
        return "{} I couldn't associate you with a wekan user.".format(get_exclamation())
    wekan_user = wekan_user[0]['wekan_id']

    valid_lists_ids = [l['id'] for l in params['config']['source_lists'] ]

    all_lane_cards = {}
    for la in lanes:
        lanecards = call_api("boards/{}/swimlanes/{}/cards".format(params['config']['board'], la))
        lanecards = [c for c in lanecards if len(c['assignees']) == 0 or wekan_user in c['assignees']]
        for lc in lanecards:
            if lc['listId'] in valid_lists_ids:
                if lc['listId'] not in all_lane_cards:
                    all_lane_cards[lc['listId']] = []
                
                all_lane_cards[lc['listId']].append(lc)

    all_list_cards = {}
    for li in lists:
        listcards = call_api("boards/{}/lists/{}/cards".format(params['config']['board'], li))
        listcards = [c for c in listcards if len(c['assignees']) == 0 or wekan_user in c['assignees']]
        if len(listcards) != 0:
            all_list_cards[li] = listcards
    
    cards = {}
    if lists and lanes:
        # both were specified so we will only display cards that match both:

        for listId, cardList in all_list_cards.items():
            currentList = []
            for card in cardList:
                if card['_id'] in [c['_id'] for c in all_lane_cards.get(listId, [])]:
                    currentList.append(card)
            if currentList:
                cards[listId] = currentList
    
    if lists and not lanes:
        cards = all_list_cards
    if lanes and not lists:
        cards = all_lane_cards
    
    if len(cards) == 0:
        return "{}! You've got no cards right now.".format(get_affirmation())
    return cards

def create_card(telegram_user, message):
    wekan_user = [ u for u in params['config']['users'] if u['telegram_id'] == telegram_user ]
    if len(wekan_user) != 1:
        return "{} I couldn't associate you with a wekan user.".format(get_exclamation())
    wekan_user = wekan_user[0]['wekan_id']

    newcard = {
        "authorId": wekan_user,
        "title": message,
        "swimlaneId": params['config']['default_lane']
    }

    card = call_api('boards/{}/lists/{}/cards'.format(params['config']['board'], params['config']['default_list']), payload=newcard)
    buttons = []

    for user in params['config']['users']:
        buttons.append([{
            'text': 'Assign to {}'.format(user['name']),
            'data': '{}:{}:{}'.format(ASSIGN, user['wekan_id'], card_to_shorthand(card['_id'], params['config']['default_list']))
        }])
    
    buttons.append([{
        'text': 'Thanks!',
        'data': REMOVE_BUTTONS,
    }])
    reply = {
        'message': "{}! I created the new task for you.".format(get_affirmation()),
        'buttons': buttons,
    }
    return reply

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
        data = requests.request(method, "{}/api/{}".format(base_url, path), json=payload, headers=headers)
        return data.json()
    else:
        data = requests.get("{}/api/{}".format(base_url, path), headers=headers)
        return data.json()
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
    auth = requests.post("{}/users/login".format(base_url), headers=headers, json=login).json()
    params['token'] = auth['token']
    params['token_expires'] = parser.parse(auth['tokenExpires'])
    params['wekan_id'] = auth['id']


def card_to_shorthand(card, list):
    id_list = [l['id'] for l in params['config']['source_lists']]
    list_id = str(id_list.index(list))
    return '{}.{}'.format(list_id, card)


def lists_to_shorthand(lists):
    id_list = [l['id'] for l in params['config']['source_lists']]
    return [str(id_list.index(l)) for l in lists]


def lanes_to_shorthand(lanes):
    id_list = [l['id'] for l in params['config']['lanes']]
    return [str(id_list.index(l)) for l in lanes]


def shorthand_to_card(shorthand):
    parts = shorthand.split('.', 1)
    list_id = int(parts[0])
    card = parts[1]
    listt = params['config']['source_lists'][list_id]['id']
    return card, listt


def shorthand_to_lists(shorthand):
    if len(shorthand) == 1 and shorthand[0] == '':
        return []
    return [params['config']['source_lists'][int(l)]['id'] for l in shorthand]


def shorthand_to_lanes(shorthand):
    if len(shorthand) == 1 and shorthand[0] == '':
        return []
    return [params['config']['lanes'][int(l)]['id'] for l in shorthand]

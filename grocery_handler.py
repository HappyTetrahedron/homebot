from base_handler import *
import datetime

from utils import PERM_ADMIN

key = "gro"

REMOVE_ITEM = 'rm'

params = {}


def setup(config, _):
    params['lists'] = config['groceries']['lists']


def matches_message(message):
    l = message.lower()
    return any([any([l.startswith(prefix) for prefix in x['add_prefices']])
                or any([l.startswith(prefix) for prefix in x['show_prefices']])
                for x in params['lists']])


def handle(message, **kwargs):
    if kwargs['permission'] < PERM_ADMIN:
        return "Sorry, you don't get to see the shopping list."
    db = kwargs['db']
    l = message.lower()
    for list_type in params['lists']:
        for prefix in list_type['add_prefices']:
            if l.startswith(prefix):
                return add_item(message[len(prefix):], db, list_type['name'])
        if any([l.startswith(prefix) for prefix in list_type['show_prefices']]):
            return grocery_list(db, list_type['name'])
    return "Whoopsie, this never happens"


def handle_button(data, **kwargs):
    db = kwargs['db']
    parts = data.split(':')
    cmd = parts[0]

    if cmd == REMOVE_ITEM:
        item_id = parts[1]
        table = db['groceries']
        item = table.find_one(id=item_id)
        if not item:
            return "Something went wrong..."
        table.delete(id=item_id)
        msg = grocery_list(db, item['list'])
        if not isinstance(msg, dict):
            msg = {
                'message': msg,
            }
        msg['answer'] = "You bought {}".format(item['name'])
        return msg
    return "Uh oh, something is off"


def add_item(item, db, list_type):
    item = " ".join(item.strip().split())
    table = db['groceries']
    new_item = {
        'name': item,
        'timestamp': datetime.datetime.now(),
        'list': list_type,
    }
    table.insert(new_item)
    return "{} was added to your {} list.".format(item, list_type)


def grocery_list(db, list_type):
    table = db['groceries']
    items = table.find(list=list_type)
    buttons = []

    for item in items:
        buttons.append([{
            'text': item['name'],
            'data': '{}:{}'.format(REMOVE_ITEM, item['id'])
        }])

    if not buttons:
        return "Your {} list is empty.".format(list_type)
    return {
        'message': "Your {} list:".format(list_type),
        'buttons': buttons,
    }


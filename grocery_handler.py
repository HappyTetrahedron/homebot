from base_handler import *
import datetime

key = "gro"

REMOVE_ITEM ='rm'


def matches_message(message):
    l = message.lower()
    return l.startswith('buy ') \
           or l.startswith('grocer') \
           or l.startswith('gift ') \
           or l.startswith('gifts') \
           or l.startswith('pack') \
           or l.startswith('shopping list')


def handle(message, db, _):
    if message.lower().startswith('buy '):
        return add_item(message[4:], db, 'shopping')
    if message.lower().startswith('grocer') \
            or message.lower().startswith('shopping list'):
        return grocery_list(db, 'shopping')
    if message.lower().startswith('gift idea') \
            or message.lower().startswith('gift list') \
            or message.lower().startswith('gifts'):
        return grocery_list(db, 'gifts')
    elif message.lower().startswith('gift '):
        return add_item(message[5:], db, 'gifts')
    if message.lower().startswith('packing'):
        return grocery_list(db, 'packing')
    elif message.lower().startswith('pack '):
        return add_item(message[5:], db, 'packing')


def handle_button(data, db, _):
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


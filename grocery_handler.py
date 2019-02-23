from base_handler import *
import datetime

key = "gro"

REMOVE_ITEM ='rm'


def matches_message(message):
    l = message.lower()
    return l.startswith('buy ') \
           or l.startswith('grocer') \
           or l.startswith('shopping list')


def handle(message, db):
    if message.lower().startswith('buy '):
        return add_item(message[4:], db)
    if message.lower().startswith('grocer') \
            or message.lower().startswith('shopping list'):
        return grocery_list(db)


def handle_button(data, db):
    parts = data.split(':')
    cmd = parts[0]

    if cmd == REMOVE_ITEM:
        item_id = parts[1]
        table = db['groceries']
        item = table.find_one(id=item_id)
        if not item:
            return "Something went wrong..."
        table.delete(id=item_id)
        msg = grocery_list(db)
        if not isinstance(msg, dict):
            msg = {
                'message': msg,
            }
        msg['answer'] = "You bought {}".format(item['name'])
        return msg
    return "Uh oh, something is off"


def add_item(item, db):
    item = " ".join(item.strip().split())
    table = db['groceries']
    new_item = {
        'name': item,
        'timestamp': datetime.datetime.now(),
    }
    table.insert(new_item)
    return "{} was added to your shopping list.".format(item)


def grocery_list(db):
    table = db['groceries']
    items = table.all()
    buttons = []

    for item in items:
        buttons.append([{
            'text': item['name'],
            'data': '{}:{}'.format(REMOVE_ITEM, item['id'])
        }])

    if not buttons:
        return "Your shopping list is empty."
    return {
        'message': "Your shopping list:",
        'buttons': buttons,
    }


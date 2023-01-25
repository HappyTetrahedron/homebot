from base_handler import *
import datetime

from utils import PERM_ADMIN
from utils import get_affirmation

key = "lip"
name = "List presets"

LIST_FLOW = 'lf'
CANCEL = 'can'
FINALIZE = 'fin'
INITIAL = 'ini'

params = {}


def setup(config, _):
    if 'listpresets' in config:
        params['lists'] = config['listpresets']
        params['enabled'] = True
    else:
        params['enabled'] = False


def help(permission):
    if not params['enabled']:
        return
    if permission < PERM_ADMIN:
        return
    return {
        'summary': "Allows you to add dynamic presets to your lists.",
        'examples': ["list preset"],
    }


def matches_message(message):
    if not params['enabled']:
        return False
    l = message.lower().strip()
    return l == 'list preset'


def handle(message, **kwargs):
    if kwargs['permission'] < PERM_ADMIN:
        return "You don't get to use the list presets."
    return initial_list_choice()


def handle_button(data, **kwargs):
    db = kwargs['db']
    parts = data.split(':')
    cmd = parts[0]

    if cmd == LIST_FLOW:
        return process_list(parts[1], parts[2], db)
    if cmd == CANCEL:
        return {
            'message': "Your list preparation has been cancelled.",
            'answer': "Aww.",
        }

    if cmd == FINALIZE:
        return process_list(parts[1], parts[2], db, finalize=True)

    if cmd == INITIAL:
        return initial_list_choice()

    return "Uh oh, something is off"


def initial_list_choice():
    buttons = []
    for list_type in params['lists']:
        buttons.append([{
            'text': list_type['name'],
            'data': '{}:{}:{}'.format(LIST_FLOW, list_type['name'], "")
        }])
    buttons.append([{
        'text': "Cancel",
        'data': CANCEL,
    }])
    return {
        'message': "All right, which list would you like to prep?",
        'buttons': buttons,
    }


def process_list(list_name, choices, db, finalize=False):
    list_preset = get_preset(list_name)
    if not list_preset:
        return "Whoa, something went wrong here"

    def process(preset_part, remaining_choices):
        composed_list = []

        for item in preset_part:
            if isinstance(item, str):
                composed_list.append(item)
            if isinstance(item, dict):
                if 'question' in item and 'answers' in item:
                    next_choice = next(remaining_choices, None)
                    if next_choice:
                        list_index = int(next_choice)
                        sub_result = process(item['answers'][list_index].get('list', []), remaining_choices)
                        if isinstance(sub_result, dict):
                            return sub_result
                        composed_list = composed_list + sub_result
                    else:
                        return item

        return composed_list

    result = process(list_preset['list'], iter(choices))

    if isinstance(result, list):
        if finalize:
            return store_list(list_name, result, db)
        else:
            return confirm_list(list_name, result, choices)
    else:
        buttons = []
        for index, option in enumerate(result['answers']):
            buttons.append([{
                'text': option['prompt'],
                'data': '{}:{}:{}{}'.format(
                    LIST_FLOW,
                    list_name,
                    choices,
                    index
                ),
            }])

        buttons.append([{
            'text': "Back",
            'data': '{}:{}:{}'.format(
                LIST_FLOW if choices else INITIAL,
                list_name,
                choices[:-1]
            ),
        }])
        buttons.append([{
            'text': "Cancel",
            'data': CANCEL,
        }])

        return {
            'message': result['question'],
            'buttons': buttons,
            'answer': get_affirmation(),

        }


def confirm_list(list_name, list_items, choices):
    message = "The following items will be added to your {} list:\n\n".format(list_name)

    for item in list_items:
        message = message + "{}\n".format(item)

    buttons = [
        [{
            'text': "Confirm",
            'data': '{}:{}:{}'.format(FINALIZE, list_name, choices),
        }],
        [{
            'text': "Back",
            'data': '{}:{}:{}'.format(
                LIST_FLOW if choices else INITIAL,
                list_name,
                choices[:-1]
            ),
        }],
        [{
            'text': "Cancel",
            'data': CANCEL,
        }],
    ]
    return {
        'message': message,
        'answer': get_affirmation(),
        'buttons': buttons,
    }


def store_list(list_name, list_items, db):
    message = "The following items were added to your {} list:\n\n".format(list_name)
    table = db['groceries']

    for item in list_items:
        item = " ".join(item.strip().split())
        new_item = {
            'name': item,
            'timestamp': datetime.datetime.now(),
            'list': list_name,
        }
        table.insert(new_item)
        message = message + "{}\n".format(item)

    return {
        'message': message,
        'answer': get_affirmation(),
    }


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


def get_preset(list_name):
    return next((x for x in params['lists'] if x['name'] == list_name), None)

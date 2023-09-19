from base_handler import *
import datetime

from utils import PERM_ADMIN
from utils import get_affirmation

LIST_FLOW = 'lf'
CANCEL = 'can'
FINALIZE = 'fin'
INITIAL = 'ini'

class ListPresetHandler(BaseHandler):
    def __init__(self, config, messenger):
        super().__init__(config, messenger, "lip", "List presets")
        if 'listpresets' in config:
            self.lists = config['listpresets']
            self.enabled = True
        else:
            self.enabled = False


    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Allows you to add dynamic presets to your lists.",
            'examples': ["list preset"],
        }


    def matches_message(self, message):
        if not self.enabled:
            return False
        l = message.lower().strip()
        return l == 'list preset'


    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "You don't get to use the list presets."
        return self.initial_list_choice()


    def handle_button(self, data, **kwargs):
        db = kwargs['db']
        parts = data.split(':')
        cmd = parts[0]

        if cmd == LIST_FLOW:
            return self.process_list(parts[1], parts[2], db)
        if cmd == CANCEL:
            return {
                'message': "Your list preparation has been cancelled.",
                'answer': "Aww.",
            }

        if cmd == FINALIZE:
            return self.process_list(parts[1], parts[2], db, finalize=True)

        if cmd == INITIAL:
            return self.initial_list_choice()

        return "Uh oh, something is off"


    def initial_list_choice(self):
        buttons = []
        for list_type in self.lists:
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
            'answer': get_affirmation(),
        }


    def process_list(self, preset_name, choices, db, finalize=False):
        list_preset = self.get_preset(preset_name)
        list_name = list_preset["listname"]
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
                return self.store_list(list_name, result, db)
            else:
                return self.confirm_list(list_name, preset_name, result, choices)
        else:
            buttons = []
            for index, option in enumerate(result['answers']):
                buttons.append([{
                    'text': option['prompt'],
                    'data': '{}:{}:{}{}'.format(
                        LIST_FLOW,
                        preset_name,
                        choices,
                        index
                    ),
                }])

            buttons.append([{
                'text': "Back",
                'data': '{}:{}:{}'.format(
                    LIST_FLOW if choices else INITIAL,
                    preset_name,
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


    def confirm_list(self, list_name, preset_name, list_items, choices):
        message = "The following items will be added to your {} list:\n\n".format(list_name)

        for item in list_items:
            message = message + "{}\n".format(item)

        buttons = [
            [{
                'text': "Confirm",
                'data': '{}:{}:{}'.format(FINALIZE, preset_name, choices),
            }],
            [{
                'text': "Back",
                'data': '{}:{}:{}'.format(
                    LIST_FLOW if choices else INITIAL,
                    preset_name,
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


    def store_list(self, list_name, list_items, db):
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


    def add_item(self, item, db, list_type):
        item = " ".join(item.strip().split())
        table = db['groceries']
        new_item = {
            'name': item,
            'timestamp': datetime.datetime.now(),
            'list': list_type,
        }
        table.insert(new_item)
        return "{} was added to your {} list.".format(item, list_type)


    def get_preset(self, list_name):
        return next((x for x in self.lists if x['name'] == list_name), None)

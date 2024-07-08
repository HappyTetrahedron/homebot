import re

from base_handler import *
import datetime

from utils import PERM_ADMIN

key = "gro"
name = "Grocery Lists"

REMOVE_ITEM = 'rm'
UPDATE_LIST = 'up'

SINGLE_WORD_PATTERN = re.compile('^\S+$', flags=re.I)


def is_single_word(string):
    return SINGLE_WORD_PATTERN.match(string)


class GroceryHandler(BaseHandler):

    def __init__(self, config, messenger):
        super().__init__(config, messenger, "gro", "Grocery Lists")
        self.lists = config['groceries']['lists']

    def help(self, permission):
        if permission >= PERM_ADMIN:
            example_list = next(iter(self.lists), None)
            example_add = next(iter(example_list['add_prefices'] or []), None)
            example_show = next(iter(example_list['show_prefices'] or []), None)

            extended_help = ""
            for list_type in self.lists:
                extended_help += "{}:\n".format(list_type['name'])
                for prefix in list_type['add_prefices']:
                    extended_help += " __{}<item>__\n".format(prefix)
                for prefix in list_type['show_prefices']:
                    extended_help += " __{}__\n".format(prefix)
                extended_help += "\n"
            return {
                'summary': "Maintains your grocery list, and other lists.",
                'examples': ["{}<item>".format(example_add), example_show],
                'extended': extended_help,
            }


    def advanced_matches_message(self, message):
        l = message.lower()
        if any([any([l.startswith(prefix) for prefix in x['add_prefices']])
                    or any([l.startswith(prefix) for prefix in x['show_prefices']])
                    for x in self.lists]):
            return MATCH_YUP

        if is_single_word(l):
            return MATCH_EH

        return MATCH_NOPE

    def handle(self, message, **kwargs):
        db = kwargs['db']
        l = message.lower()
        for list_type in self.lists:
            for prefix in list_type['add_prefices']:
                if l.startswith(prefix):
                    if ('users' in list_type and str(kwargs['actor_id']) in list_type['users']) \
                        or ('users' not in list_type and kwargs['permission'] >= PERM_ADMIN):
                        return self.add_item(message[len(prefix):], db, list_type['name'])
                    else:
                        return "Sorry, you don't get to add to this list."
            if any([l.startswith(prefix) for prefix in list_type['show_prefices']]):
                if ('users' in list_type and str(kwargs['actor_id']) in list_type['users']) \
                    or ('users' not in list_type and kwargs['permission'] >= PERM_ADMIN):
                    return self.grocery_list(db, list_type['name'])
                else:
                    return "Sorry, you don't get to see this list."

        if is_single_word(l):
            list_type = self.lists[0]
            if ('users' in list_type and str(kwargs['actor_id']) in list_type['users']) \
                    or ('users' not in list_type and kwargs['permission'] >= PERM_ADMIN):
                return self.add_item(message, db, list_type['name'])
            else:
                return "No."

        return "Whoopsie, this never happens"


    def handle_button(self, data, **kwargs):
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
            msg = self.grocery_list(db, item['list'])
            if not isinstance(msg, dict):
                msg = {
                    'message': msg,
                }
            msg['answer'] = "You bought {}".format(item['name'])
            return msg
        if cmd == UPDATE_LIST:
            msg = self.grocery_list(db, parts[1])
            if not isinstance(msg, dict):
                msg = {
                    'message': msg,
                }
            msg['answer'] = "Updated."
            return msg
        return "Uh oh, something is off"


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


    def grocery_list(self, db, list_type):
        table = db['groceries']
        items = table.find(list=list_type)
        buttons = []

        for item in items:
            buttons.append([{
                'text': item['name'],
                'data': '{}:{}'.format(REMOVE_ITEM, item['id'])
            }])

        buttons.append([{
                'text': "update list",
                'data': '{}:{}'.format(UPDATE_LIST, list_type)
        }])

        if len(buttons) <= 1:
            msg = "Your {} list is empty.".format(list_type)
        else:
            msg = "Your {} list:".format(list_type)
        return {
            'message': msg,
            'buttons': buttons,
        }
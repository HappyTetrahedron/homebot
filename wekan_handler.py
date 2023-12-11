from base_handler import *
import requests
from dateutil import parser
import datetime
import logging
from utils import PERM_ADMIN
from utils import get_exclamation
from utils import get_affirmation

logger = logging.getLogger(__name__)

MARK_DONE = 'md'
DISMISS_LIST = 'rm'
REMOVE_BUTTONS = 'rd'
UPDATE = 'up'
ASSIGN = 'ass'

CARD_SYNONYMS = ['cards', 'todos', 'tasks'] # all 5 characters - if any of different length are introduced fix code below!

class WekanHandler(BaseHandler):
    
    def __init__(self, config, messenger):
        super().__init__(config, messenger, "wekan", "Wekan Integration")
        if 'wekan' in config:
            self.config = config['wekan']
            self.enabled = True
            self.token_expires = 0
        else:
            self.enabled = False


    def matches_message(self, message):
        m = message.lower()
        if not self.enabled:
            return False
        if m in CARD_SYNONYMS:
            return True
        if any([m.endswith(' ' + it) for it in CARD_SYNONYMS]):
            return True
        if m.startswith('do '):
            return True
        if m.startswith('toggle task report'):
            return True
        return False


    def help(self, permission):
        if not self.enabled:
            return
        if permission >= PERM_ADMIN:
            return {
                'summary': "Shows you an overview of your wekan board cards.",
                'examples': [
                    "cards",
                    "{} cards".format(self.config['source_lists'][0]['names'][0]),
                    "{} cards".format(self.config['lanes'][0]['names'][0]),
                    "do this very important task",
                    "do eventually this low-prio task",
                    "toggle task report",
                ],
            }
    

    def handle(self, message, **kwargs):
        m = message.lower()
        if m in CARD_SYNONYMS:
            m = ' cards'
        if m.startswith('do '):
            if m.startswith('do eventually '):
                task = message[14:]
                list_id = self.config['backlog_list']
            else:
                task = message[3:]
                list_id = self.config['default_list']
            return self.create_card(kwargs['actor_id'], task, list_id)
        if m.startswith('toggle task report'):
            return self.toggle_report(kwargs['actor_id'], kwargs['db'])
        elif any([m.endswith(' ' + it) for it in CARD_SYNONYMS]):
            l = m[:-6] # IMPORTANT this only happens to work by chance since all synonyms are 5 characters
            lanes = []
            for lane in self.config['lanes']:
                for name in lane['names']:
                    if name in l:
                        lanes.append(lane['id'])
            lists = []
            for list_ in self.config['source_lists']:
                for name in list_['names']:
                    if name in l:
                        lists.append(list_['id'])
            if not lanes and not lists:
                lanes = [l['id'] for l in self.config['lanes']]
                lists = [l['id'] for l in self.config['source_lists']]

            return self.get_card_buttons(kwargs['actor_id'], lists, lanes)
        return 'Something went wrong'


    def handle_button(self, data, **kwargs):
        data = data.split(':', 1)
        cmd = data[0]

        if cmd == REMOVE_BUTTONS:
            return {
                'message': "{}! I created the new task for you.".format(get_affirmation()),
                'answer': get_affirmation(),
            }
        if cmd == DISMISS_LIST:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[0].split(','))
            lanes = self.shorthand_to_lanes(args[1].split(','))
            resp = self.get_card_text(kwargs['actor_id'], lists, lanes)
            resp['answer'] = get_affirmation()
            return resp

        if cmd == UPDATE:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[0].split(','))
            lanes = self.shorthand_to_lanes(args[1].split(','))
            resp = self.get_card_buttons(kwargs['actor_id'], lists, lanes)
            resp['answer'] = get_affirmation()
            return resp

        if cmd == MARK_DONE:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[1].split(','))
            lanes = self.shorthand_to_lanes(args[2].split(','))
            card_shorthand = args[0]
            card_id, list_id = self.shorthand_to_card(card_shorthand)

            payload = {
                'listId': self.config['target_list']
            }

            self.call_api('boards/{}/lists/{}/cards/{}'.format(self.config['board'], list_id, card_id), payload, method='PUT')

            resp = self.get_card_buttons(kwargs['actor_id'], lists, lanes)
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
            user = [ u for u in self.config['users'] if u['wekan_id'] == user_id ]
            if len(user) < 1:
                user = {}
            else:
                user = user[0]
            card_id, list_id = self.shorthand_to_card(args[1])
            data = {
                '_id': card_id,
                'assignees': [user_id],
            }
            r = self.call_api('boards/{}/lists/{}/cards/{}'.format(self.config['board'], list_id, card_id), data, method='PUT')
            return {
                'message': "{}! I created the new task for you and assigned it to {}.".format(get_affirmation(), user.get('name', '... someone')),
                'answer': get_affirmation(),
            }



    def get_card_text(self, telegram_user, lists, lanes):
        cards = self.get_my_cards(telegram_user, lists, lanes)
        if isinstance(cards, str):
            return cards

        msg = {
            'message': '\n'.join([ '\n'.join([c['title'] for c in subcards]) for subcards in cards.values() ]),
            'buttons': [[{
                'text': "Expand",
                'data': '{}:{}:{}'.format(UPDATE, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            }]],
        }
        return msg

    def get_card_buttons(self, telegram_user, lists, lanes):
        cards = self.get_my_cards(telegram_user, lists, lanes)
        if isinstance(cards, str):
            return cards
        buttons = []
        for li, cardlist in cards.items():
            for card in cardlist:
                buttons.append([{
                    'text': card['title'],
                    'data': '{}:{}:{}:{}'.format(MARK_DONE, self.card_to_shorthand(card['_id'], li), ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
                }])
        buttons.append([
            {
                'text': "Update",
                'data': '{}:{}:{}'.format(UPDATE, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            },
            {
                'text': "Done",
                'data': '{}:{}:{}'.format(DISMISS_LIST, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            }
        ])

        return {
            'message': "I found the following cards:",
            'buttons': buttons,
        }


    def get_my_cards(self, telegram_user, lists, lanes):
        wekan_user = [ u for u in self.config['users'] if u['telegram_id'] == telegram_user ]

        if len(wekan_user) != 1:
            return "{} I couldn't associate you with a wekan user.".format(get_exclamation())
        wekan_user = wekan_user[0]['wekan_id']

        valid_lists_ids = [l['id'] for l in self.config['source_lists'] ]

        all_lane_cards = {}
        for la in lanes:
            lanecards = self.call_api("boards/{}/swimlanes/{}/cards".format(self.config['board'], la))
            lanecards = [c for c in lanecards if len(c['assignees']) == 0 or wekan_user in c['assignees']]
            for lc in lanecards:
                if lc['listId'] in valid_lists_ids:
                    if lc['listId'] not in all_lane_cards:
                        all_lane_cards[lc['listId']] = []

                    all_lane_cards[lc['listId']].append(lc)

        all_list_cards = {}
        for li in lists:
            listcards = self.call_api("boards/{}/lists/{}/cards".format(self.config['board'], li))
            listcards = [c for c in listcards if len(c['assignees']) == 0 or wekan_user in c['assignees']]
            if len(listcards) != 0:
                all_list_cards[li] = listcards

        cards = {}
        if lists and lanes:
            # both were specified, so we will only display cards that match both:

            for listId, cardList in all_list_cards.items():
                current_list = []
                for card in cardList:
                    if card['_id'] in [c['_id'] for c in all_lane_cards.get(listId, [])]:
                        current_list.append(card)
                if current_list:
                    cards[listId] = current_list

        if lists and not lanes:
            cards = all_list_cards
        if lanes and not lists:
            cards = all_lane_cards

        if len(cards) == 0:
            return "{}! You've got no cards right now.".format(get_affirmation())
        return cards

    def create_card(self, telegram_user, message, list_id):
        wekan_user = [ u for u in self.config['users'] if u['telegram_id'] == telegram_user ]
        if len(wekan_user) != 1:
            return "{} I couldn't associate you with a wekan user.".format(get_exclamation())
        wekan_user = wekan_user[0]['wekan_id']

        newcard = {
            "authorId": wekan_user,
            "title": message,
            "swimlaneId": self.config['default_lane']
        }

        card = self.call_api('boards/{}/lists/{}/cards'.format(self.config['board'], list_id), payload=newcard)
        buttons = []

        if list_id == self.config['default_list']:
            for user in self.config['users']:
                buttons.append([{
                    'text': 'Assign to {}'.format(user['name']),
                    'data': '{}:{}:{}'.format(ASSIGN, user['wekan_id'], self.card_to_shorthand(card['_id'], list_id))
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

    def call_api(self, path, payload=None, method='GET'):
        base_url = self.config['url']
        if not self.token_valid():
            self.login()
        headers = {
            'Authorization': 'Bearer {}'.format(self.token),
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


    def toggle_report(self, actor, db):
        table = db['wekan']
        entry = table.find_one(actor=actor)
        if not entry:
            entry= {
                'actor': actor,
                'enabled': True,
                'next_message': self.get_next_reminder_date(),
            }
            table.insert(entry)
        else:
            entry['enabled'] = not entry['enabled']
            entry['next_message'] = self.get_next_reminder_date(),
            table.update(entry, ['actor'])

        if entry['enabled']:
            return "You will receive daily task reports."
        return "You will no longer receive task reports."


    def token_valid(self): 
        return self.token_expires and self.token_expires > datetime.datetime.now().astimezone()


    def login(self):
        base_url = self.config['url']
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        login = {
            'username': self.config['username'],
            'password': self.config['password'],
        }
        auth = requests.post("{}/users/login".format(base_url), headers=headers, json=login).json()
        self.token = auth['token']
        self.token_expires = parser.parse(auth['tokenExpires'])
        self.wekan_id = auth['id']


    def card_to_shorthand(self, card, list_id):
        list_ids = [l['id'] for l in self.config['source_lists']]
        list_index = list_ids.index(list_id)
        return '{}.{}'.format(list_index, card)


    def lists_to_shorthand(self, lists):
        list_ids = [l['id'] for l in self.config['source_lists']]
        return [str(list_ids.index(l)) for l in lists]


    def lanes_to_shorthand(self, lanes):
        lane_ids = [l['id'] for l in self.config['lanes']]
        return [str(lane_ids.index(l)) for l in lanes]


    def shorthand_to_card(self, shorthand):
        parts = shorthand.split('.', 1)
        list_index = int(parts[0])
        card = parts[1]
        list_id = self.config['source_lists'][list_index]['id']
        return card, list_id


    def shorthand_to_lists(self, shorthand):
        if len(shorthand) == 1 and shorthand[0] == '':
            return []
        return [self.config['source_lists'][int(l)]['id'] for l in shorthand]


    def shorthand_to_lanes(self, shorthand):
        if len(shorthand) == 1 and shorthand[0] == '':
            return []
        return [self.config['lanes'][int(l)]['id'] for l in shorthand]


    def get_next_reminder_date(self):
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        tomorrow_morning = datetime.datetime(
            year=tomorrow.year,
            month=tomorrow.month,
            day=tomorrow.day,
            hour=5,
            minute=55,
        )
        return tomorrow_morning


    def run_periodically(self, db):
        debug = self._debug
        table = db['wekan']
        send = self._messenger.send_message
        if debug:
            logger.info("Querying wekan reports...")

        now = datetime.datetime.now()
        reminders = db.query('SELECT * FROM wekan WHERE enabled IS TRUE AND next_message < :now', now=now)

        count = 0
        for reminder in reminders:
            count += 1
            if debug:
                logger.info("Sending wekan report {}".format(count))
            # this is so stupid I can't even
            # dataset returns dates as string but only accepts them as datetime
            reminder['next_message'] = datetime.datetime.strptime(reminder['next_message'], '%Y-%m-%d %H:%M:%S.%f')

            lists = [l['id'] for l in self.config['source_lists']]
            msg = self.get_card_text(reminder['actor'], lists, [])
            msg['message'] = "Here is your daily task report:\n\n" + msg['message']

            send(msg, key=self.key, recipient_id=reminder['actor'] if 'actor' in reminder else None)

            reminder['next_message'] = self.get_next_reminder_date()

            if debug:
                logger.info("Updating report {}".format(count))
            table.update(reminder, ['actor'])
            if debug:
                logger.info("Finished report {}".format(count))
        if debug:
            logger.info("Sent out {} reports".format(count))

from base_handler import *
import datetime
import logging
import random
from utils import PERM_ADMIN
from utils import get_exclamation
from utils import get_affirmation
from wekan_service import WekanService

logger = logging.getLogger(__name__)

MARK_DONE = 'md'
DISMISS_LIST = 'rm'
REMOVE_BUTTONS = 'rd'
UPDATE = 'up'
BUMP = 'b'
PROGRESS = 'p'
SEND_BUMP_LIST = 'sb'
ASSIGN = 'ass'

BUMP_1_DAY = "d"
BUMP_3_DAYS = "D"
BUMP_1_WEEK = "w"
BUMP_12_DAYS = "W"
BUMP_1_MONTH = "m"
BUMP_WHENEVER = "?"

CARD_SYNONYMS = ['cards', 'todos', 'tasks'] # all 5 characters - if any of different length are introduced fix code below!

class WekanHandler(BaseHandler):

    wekan_service: WekanService

    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="wekan", name="Wekan Integration")
        self.wekan_service = service_hub.wekan
        if 'wekan' in config:
            self.config = config['wekan']
            self.enabled = True
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
        if m.startswith('i do '):
            return True
        if m.startswith('we do '):
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
        if m.startswith('i do'):
            if m.startswith('i do eventually '):
                task = message[16:]
                list_id = self.config['backlog_list']
            else:
                task = message[5:]
                list_id = self.config['default_list']
            return self.create_card(kwargs['actor_id'], task, list_id, assign_to_me=True)
        if m.startswith('we do'):
            if m.startswith('we do eventually '):
                task = message[17:]
                list_id = self.config['backlog_list']
            else:
                task = message[6:]
                list_id = self.config['default_list']
            return self.create_cards_for_everyone(kwargs['actor_id'], task, list_id)
        if m.startswith('toggle task report'):
            return self.toggle_report(kwargs['actor_id'], kwargs['db'])
        elif any([m.endswith(' ' + it) for it in CARD_SYNONYMS]):
            l = m[:-6] # IMPORTANT this only happens to work by chance since all synonyms are 5 characters
            lanes = []
            for lane in self.config['lanes']:
                for name in lane.get('names', []):
                    if name in l:
                        lanes.append(lane['id'])
            lists = []
            for list_ in self.config['source_lists']:
                for name in list_.get('names', []):
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
            if isinstance(resp, str):
                resp = {'message': resp}
            resp['answer'] = get_affirmation()
            return resp

        if cmd == UPDATE:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[0].split(','))
            lanes = self.shorthand_to_lanes(args[1].split(','))
            resp = self.get_card_buttons(kwargs['actor_id'], lists, lanes)
            if isinstance(resp, str):
                resp = {'message': resp}
            resp['answer'] = get_affirmation()
            return resp

        if cmd == SEND_BUMP_LIST:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[0].split(','))
            lanes = self.shorthand_to_lanes(args[1].split(','))
            resp = self.get_card_bump_buttons(kwargs['actor_id'], lists, lanes)
            if isinstance(resp, str):
                resp = {'message': resp}
            resp['answer'] = get_affirmation()
            return resp

        if cmd == MARK_DONE:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[1].split(','))
            lanes = self.shorthand_to_lanes(args[2].split(','))
            card_shorthand = args[0]
            card_id, list_id = self.shorthand_to_card(card_shorthand)

            self.wekan_service.move_card_to_done(list_id, card_id)

            resp = self.get_card_buttons(kwargs['actor_id'], lists, lanes)
            if isinstance(resp, str):
                return {
                    'message': resp,
                    'answer': get_affirmation(),
                }

            resp['answer'] = get_affirmation()
            return resp

        if cmd == PROGRESS:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[1].split(','))
            lanes = self.shorthand_to_lanes(args[2].split(','))
            card_shorthand = args[0]
            card_id, list_id = self.shorthand_to_card(card_shorthand)

            self.wekan_service.move_card_to_in_progress(list_id, card_id)

            resp = self.get_card_bump_buttons(kwargs['actor_id'], lists, lanes)
            if isinstance(resp, str):
                return {
                    'message': resp,
                    'answer': get_affirmation(),
                }

            resp['answer'] = get_affirmation()
            return resp

        if cmd == ASSIGN:
            args = data[1].split(':')
            telegram_user_id = args[0]
            name = self.wekan_service.get_wekan_user_name(telegram_user_id) or '... someone'

            card_id, list_id = self.shorthand_to_card(args[1])
            self.wekan_service.assign_card(list_id, card_id, telegram_user_id)

            return {
                'message': f"{get_affirmation()}! I created the new task for you and assigned it to {name}.",
                'answer': get_affirmation(),
            }

        if cmd == BUMP:
            args = data[1].split(':')
            lists = self.shorthand_to_lists(args[2].split(','))
            lanes = self.shorthand_to_lanes(args[3].split(','))
            card_shorthand = args[1]
            bump_code = args[0]
            card_id, list_id = self.shorthand_to_card(card_shorthand)

            now = datetime.datetime.now()
            morning = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=2)
            start_date = morning

            if bump_code == BUMP_1_DAY:
                start_date += datetime.timedelta(days=1)
            elif bump_code == BUMP_3_DAYS:
                start_date += datetime.timedelta(days=3)
            elif bump_code == BUMP_1_WEEK:
                start_date += datetime.timedelta(days=7)
            elif bump_code == BUMP_12_DAYS:
                start_date += datetime.timedelta(days=12)
            elif bump_code == BUMP_1_MONTH:
                start_date += datetime.timedelta(days=30)
            else:
                start_date += datetime.timedelta(days=random.randint(3, 30))

            self.wekan_service.move_card_to_backlog(list_id, card_id, start_date)

            resp = self.get_card_bump_buttons(kwargs['actor_id'], lists, lanes)
            if isinstance(resp, str):
                return {
                    'message': resp,
                    'answer': get_affirmation(),
                }

            resp['answer'] = get_affirmation()
            return resp

    def get_card_text(self, telegram_user, lists, lanes):
        cards = self.wekan_service.get_cards(telegram_user, lists, lanes)
        if not cards:
            return f"{get_affirmation()}! You've got no cards right now."
        msg = {
            'message': '\n'.join([ '\n'.join([self.format_card_name(c, li) for c in subcards]) for li, subcards in cards.items() ]),
            'buttons': [[{
                'text': "Expand",
                'data': '{}:{}:{}'.format(UPDATE, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            }]],
        }
        return msg

    def get_card_buttons(self, telegram_user, lists, lanes):
        cards = self.wekan_service.get_cards(telegram_user, lists, lanes)
        if not cards:
            return f"{get_affirmation()}! You've got no cards right now."
        buttons = []
        for li, cardlist in cards.items():
            for card in cardlist:
                buttons.append([{
                    'text': self.format_card_name(card, li),
                    'data': '{}:{}:{}:{}'.format(MARK_DONE, self.card_to_shorthand(card['_id'], li), ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
                }])
        buttons.append([
            {
                'text': "Update",
                'data': '{}:{}:{}'.format(UPDATE, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            },
            {
                'text': "Bounce",
                'data': '{}:{}:{}'.format(SEND_BUMP_LIST, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            },
            {
                'text': "Done",
                'data': '{}:{}:{}'.format(DISMISS_LIST, ','.join(self.lists_to_shorthand(lists)), ','.join(self.lanes_to_shorthand(lanes))),
            },
        ])

        return {
            'message': "I found the following cards:",
            'buttons': buttons,
        }

    def get_card_bump_buttons(self, telegram_user, lists, lanes):
        cards = self.wekan_service.get_cards(telegram_user, lists, lanes)
        if not cards:
            return f"{get_affirmation()}! You've got no cards right now."
        buttons = []
        lists_string = ','.join(self.lists_to_shorthand(lists))
        lanes_string = ','.join(self.lanes_to_shorthand(lanes))
        for li, cardlist in cards.items():
            for card in cardlist:
                card_id_shorthand = self.card_to_shorthand(card['_id'], li)
                buttons.append([{
                    'text': self.format_card_name(card, li),
                    'data': f'{MARK_DONE}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                }])
                buttons.append([
                    {
                        'text': "▶️",
                        'data': f'{PROGRESS}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                    {
                        'text': "+1d",
                        'data': f'{BUMP}:{BUMP_1_DAY}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                    {
                        'text': "+3d",
                        'data': f'{BUMP}:{BUMP_3_DAYS}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                    {
                        'text': "+1w",
                        'data': f'{BUMP}:{BUMP_1_WEEK}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                    {
                        'text': "+12d",
                        'data': f'{BUMP}:{BUMP_12_DAYS}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                    {
                        'text': "+1m",
                        'data': f'{BUMP}:{BUMP_1_MONTH}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                    {
                        'text': "🌈",
                        'data': f'{BUMP}:{BUMP_WHENEVER}:{card_id_shorthand}:{lists_string}:{lanes_string}',
                    },
                ])
        buttons.append([
            {
                'text': "Update",
                'data': f'{SEND_BUMP_LIST}:{lists_string}:{lanes_string}',
            },
            {
                'text': "Back",
                'data': f'{UPDATE}:{lists_string}:{lanes_string}',
            },
        ])

        return {
            'message': "I found the following cards:",
            'buttons': buttons,
        }

    def format_card_name(self, card, list_id):
        list_prefix = ""
        list_suffix = ""
        for source in self.config["source_lists"]:
            if source["id"] == list_id:
                list_prefix = source.get("prefix", "")
                list_suffix = source.get("suffix", "")
        lane_prefix = ""
        lane_suffix = ""
        for lane in self.config["lanes"]:
            if lane["id"] == card.get("swimlaneId", "invalid"):
                lane_prefix = lane.get("prefix", "")
                lane_suffix = lane.get("suffix", "")
        return "{}{} {} {}{}".format(list_prefix, lane_prefix, card['title'], lane_suffix, list_suffix).strip()

    def create_card(self, telegram_user, message, list_id, assign_to_me=False):
        card_id = self.wekan_service.create_card(telegram_user, message, list_id, assign_to_creator=assign_to_me)
        if not card_id:
            return f"{get_exclamation()} I couldn't associate you with a wekan user."

        buttons = []

        if list_id == self.config['default_list'] and not assign_to_me:
            for user in self.config['users']:
                buttons.append([{
                    'text': 'Assign to {}'.format(user['name']),
                    'data': f'{ASSIGN}:{user['telegram_id']}:{self.card_to_shorthand(card_id, list_id)}',
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

    def create_cards_for_everyone(self, telegram_user, message, list_id):
        for user in self.config['users']:
            card_id = self.wekan_service.create_card(telegram_user, message, list_id)
            if not card_id:
                return f"{get_exclamation()} I couldn't associate you with a wekan user."
            telegram_user_id = user['telegram_id']
            self.wekan_service.assign_card(list_id, card_id, telegram_user_id)

        reply = {
            'message': "{}! I created a new task for everyone.".format(get_affirmation()),
            'buttons': [[{
                'text': 'Thanks!',
                'data': REMOVE_BUTTONS,
            }]],
        }
        return reply

    def toggle_report(self, actor, db):
        table = db['wekan']
        entry = table.find_one(actor=actor)
        if not entry:
            entry = {
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
        send = self._messenger.send_message_from_thread
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
            if isinstance(msg, dict):
                # only send if there are actual tasks, which is conveniently only the case if msg is a dict
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

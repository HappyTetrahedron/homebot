from base_handler import *
import re
import threading
import parsedatetime
import datetime
import dataset
from utils import get_affirmation

# PATTERN = re.compile('^remind\s+(?:me\s+)?(.+?)(?:\s+to|:)\s+(.+?)\s*$',
PATTERN = re.compile('^remind(?:\s+me)?\s+(.+?)\s*(to|:|that)\s+(.+?)\s*$',
                     flags=re.I)
params = {}

key = 'rem'

calendar = parsedatetime.Calendar()

UNITS = [
    'min',
    'h',
    'day',
    'week',
    'month',
    'year',
]

REMOVE_BUTTONS = 'rb'
REMOVE_REMINDER = 'rm'
REMOVE_PERIODIC_REMINDER = 'rmp'
SNOOZE_REMINDER = 'sn'


def setup(config, send_message):
    params['db'] = dataset.connect('sqlite:///{}'.format(config['db']))
    params['debug'] = config['debug']
    params['sendmsg'] = send_message
    params['exit'] = threading.Event()

    t = threading.Thread(target=run)
    t.start()


def teardown():
    params['exit'].set()


def matches_message(message):
    return PATTERN.match(message) is not None


def handle(message, db):
    match = PATTERN.match(message)
    if not match:
        return "This wasn't supposed to happen."

    groups = match.groups()
    time_string = groups[0]
    separator_word = groups[1]
    subject = groups[2]

    if 'every' in time_string or 'each' in time_string:
        reminder = create_periodic_reminder(time_string, subject, separator_word)

        msg = "I set up your reminder for every {}{}. The first one will happen on ".format(
            "{} ".format(reminder['interval']) if reminder['interval'] > 1 else "",
            unit_to_readable(reminder['unit'], reminder['interval'] == 1),
        ) + '{}'

    else:
        reminder = create_onetime_reminder(time_string, subject, separator_word)
        msg = "I set up your reminder for {}"

    table = db['reminders']
    reminder_id = table.insert(reminder)
    return {
        'message': msg.format(
            reminder['next'].strftime("%A, %B %-d %Y at %-H:%M")
        ),
        'buttons': [[{
            'text': "Remove this reminder",
            'data': "{}:{}".format(reminder_id, REMOVE_REMINDER)
        }]],
    }


def handle_button(data, db):
    parts = data.split(':')
    reminder_id = int(parts[0])
    method = parts[1]

    table = db['reminders']
    reminder = table.find_one(id=reminder_id)
    answer = {}
    if method == REMOVE_REMINDER:
        table.delete(id=reminder_id)
        answer = {
            'answer': "Reminder deleted",
            'message': "This reminder was deleted.",
        }
    if method == REMOVE_BUTTONS:
        answer = {
            'answer': get_affirmation(),
            'message': reminder_to_string(reminder),
        }
    if method == REMOVE_PERIODIC_REMINDER:
        table.delete(id=reminder_id)
        answer = {
            'answer': "Reminder deleted",
            'message': "{}\n\nThis periodic reminder was deleted.".format(reminder_to_string(reminder)),
        }
    if method == SNOOZE_REMINDER:
        reminder['next'] = reminder['next'] + datetime.timedelta(minutes=1)
        reminder['active'] = True
        table.update(reminder, ['id'])
        answer = {
            'answer': "Reminder snoozed",
            'message': "{}\n\nThis reminder was snoozed.".format(reminder_to_string(reminder))
        }
    return answer


def create_periodic_reminder(time_string, subject, separator_word):
    now = datetime.datetime.now()
    time_string_parts = time_string.split()

    interval = 0
    unit = ""
    rest = ""

    for i, part in enumerate(time_string_parts):
        if unit:
            break
        if part.isnumeric():
            interval = int(part)
        if part == 'other':
            interval = 2
        for potential_unit in UNITS:
            if part.lower().startswith(potential_unit):
                unit = potential_unit
                rest = " ".join(time_string_parts[i+1:])
    if not unit:
        unit = 'week'
        rest = " ".join(time_string_parts[1:])
    if not interval:
        interval = 1

    if rest:
        date_time, parsed = calendar.parseDT(rest)
        if parsed == 0:
            if unit == 'month':
                day = int(re.sub('\D', '', rest))
                if 0 < day < 29:  # sorry we can't handle february otherwise.
                    date_time = datetime.datetime(year=now.year, month=now.month, day=day, hour=7, minute=0)
                else:
                    return "Oh no, I couldn't understand what you mean by \"{}\". Note that you can only use" \
                           "dates (days of month) between 1 and 28, unfortunately.".format(rest)
            else:
                return "Oh no, I couldn't understand what you mean by \"{}\".".format(rest)

        if parsed == 1:
            date_time = datetime.datetime.combine(date_time.date(), datetime.time(hour=7, minute=0))

        if parsed == 2:
            # time without date - only makes sense if unit is day or hour:
            if unit != 'day' and unit != 'hour':
                return "Oh no, I couldn't understand what you mean by \"{}\". Note that you can only set" \
                       "a time (without a weekday or date) if your reminder is every X days or hours".format(rest)
    else:
        if unit == 'min':
            date_time = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=now.hour,
                                          minute=now.minute)
        elif unit == 'h':
            date_time = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=now.hour)
        elif unit == 'day' or unit == 'week':
            date_time = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=7)
        elif unit == 'month':
            date_time = datetime.datetime(year=now.year, month=now.month, day=1, hour=7)
        elif unit == 'year':
            date_time = datetime.datetime(year=now.year + 1, month=1, day=1, hour=7)

    # phew.
    reminder = {
        'next': date_time,
        'subject': subject,
        'active': True,
        'periodic': True,
        'interval': interval,
        'unit': unit,
        'separator': separator_word,
    }

    if date_time < now:
        advance_periodic_reminder(reminder)
    return reminder


def create_onetime_reminder(time_string, subject, separator_word):
    now = datetime.datetime.now()
    date_time, parsed = calendar.parseDT(time_string)
    if parsed == 0:
        return "Sorry, I don't understand what you mean by \"{}\".".format(time_string)
    if parsed == 1:
        # date without time - assume morning
        date_time = datetime.datetime.combine(date_time.date(), datetime.time(hour=7, minute=0))
    if parsed == 2:
        # time without date - assume next time that time comes up
        if now > date_time:
            date_time += datetime.timedelta(days=1)
    reminder = {
        'next': date_time,
        'subject': subject,
        'active': True,
        'periodic': False,
        'separator': separator_word,
    }
    return reminder


def advance_periodic_reminder(reminder):
    if not reminder['periodic']:
        return
    unit = reminder['unit']
    interval = reminder['interval']
    if unit == 'min':
        reminder['next'] += datetime.timedelta(minutes=interval)
    if unit == 'h':
        reminder['next'] += datetime.timedelta(hours=interval)
    if unit == 'day':
        reminder['next'] += datetime.timedelta(days=interval)
    if unit == 'week':
        reminder['next'] += datetime.timedelta(days=7*interval)
    if unit == 'month':
        reminder['next'] = advance_by_a_month(reminder['next'], interval)
    if unit == 'year':
        dt = reminder['next']
        reminder['next'] = datetime.datetime(dt.year + interval, dt.month, dt.day, dt.hour, dt.minute)


def advance_by_a_month(date_time, months):
    one_day = datetime.timedelta(days=1)
    one_month_later = date_time + one_day
    current_month = date_time.month
    while months > 0:
        while one_month_later.month == current_month:  # advance to start of next month
            one_month_later += one_day
        months -= 1
        current_month = one_month_later.month
    target_month = one_month_later.month
    while one_month_later.day < date_time.day:  # advance to appropriate day
        one_month_later += one_day
        if one_month_later.month != target_month:  # gone too far
            one_month_later -= one_day
            break
    return one_month_later


def unit_to_readable(unit, singular=False):
    if unit == 'h':
        return 'hour' if singular else 'hours'
    if unit == 'min':
        return 'minute' if singular else 'minutes'
    return unit if singular else unit + 's'


def reminder_to_string(reminder):
    return "Remember{} {}".format(
        ' to' if 'separator' not in reminder or not reminder['separator'] else
        reminder['separator'] if len(reminder['separator']) == 1 else
        " {}".format(reminder['separator']),
        reminder['subject'])


def schedule_pending():
    debug = params['debug']
    db = params['db']
    table = db['reminders']
    send = params['sendmsg']
    if debug:
        print("Querying reminders...")

    now = datetime.datetime.now()
    reminders = db.query('SELECT * FROM reminders WHERE active IS TRUE AND next < :now', now=now)

    count = 0
    for reminder in reminders:
        count += 1
        if debug:
            print("Sending reminder {}".format(count))
        # this is so stupid I can't even
        # dataset returns dates as string but only accepts them as datetime
        reminder['next'] = datetime.datetime.strptime(reminder['next'], '%Y-%m-%d %H:%M:%S.%f')

        msg = reminder_to_string(reminder)

        if reminder['periodic']:
            advance_periodic_reminder(reminder)
            buttons = [[{
                'text': "Remove this reminder",
                'data': '{}:{}'.format(reminder['id'], REMOVE_PERIODIC_REMINDER)
            }]]
        else:
            reminder['active'] = False
            buttons = [
                [{
                    'text': 'Got it!',
                    'data': '{}:{}'.format(reminder['id'], REMOVE_BUTTONS),
                }],
                [{
                    'text': "Remind me again tomorrow",
                    'data': '{}:{}'.format(reminder['id'], SNOOZE_REMINDER),
                }]
            ]
        send({
            'message': msg,
            'buttons': buttons,
        }, key=key)

        if debug:
            print("Updating reminder {}".format(count))
        table.update(reminder, ['id'])
        if debug:
            print("Finished reminder {}".format(count))
    if debug:
        print("Sent out {} reminders".format(count))


def run():
    while not params['exit'].is_set():
        schedule_pending()
        params['exit'].wait(60)




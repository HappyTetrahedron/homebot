from base_handler import *
import json
import re
import parsedatetime
import datetime
import logging
from utils import get_affirmation

PATTERN = re.compile('^remind(?:\s+me)?\s+(.+?)\s*(to|:|that|about)\s+(.+?)\s*$', flags=re.I)
params = {}

key = 'rem'
name = "Reminders"

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

SNOOZE_REMINDER_HOUR = 'snh'
SNOOZE_REMINDER_6_HOURS = 'sn6h'
SNOOZE_REMINDER_DAY = 'sn'
SNOOZE_REMINDER_WEEK = 'snw'
SNOOZE_REMINDERS = {
    SNOOZE_REMINDER_HOUR: {
        'button': "+1h",
        'amount': "1 hour",
        'delta': datetime.timedelta(hours=1),
    },
    SNOOZE_REMINDER_6_HOURS: {
        'button': "+6h",
        'amount': "6 hours",
        'delta': datetime.timedelta(hours=6),
    },
    SNOOZE_REMINDER_DAY: {
        'button': "+1d",
        'amount': "1 day",
        'delta': datetime.timedelta(days=4),
    },
    SNOOZE_REMINDER_WEEK: {
        'button': "+1w",
        'amount': "1 week",
        'delta': datetime.timedelta(weeks=1),
    },
}

DELETE_MESSAGE = 'dm'


def help(permission):
    return {
        'summary': "Makes sure you never forget things again.",
        'examples': [
            "Remind me <time> to <thing>",
            "Remind me tomorrow to do laundry",
            "Remind me in three days to take out trash",
            "Remind me on July 15 at 13:40 to call mom",
            "Remind me each Wednesday to water the plants",
            "Remind me every year on August 18 that it's my birthday",
        ],
    }


def matches_message(message):
    return PATTERN.match(message) is not None


def handle(message, **kwargs):
    time = datetime.datetime.fromisoformat(kwargs['time'])
    
    actor_id = kwargs['actor_id']
    match = PATTERN.match(message)
    if not match:
        return "This wasn't supposed to happen."

    groups = match.groups()
    time_string = groups[0]
    separator_word = groups[1]
    if separator_word == 'about':
        separator_word = ''
    subject = groups[2]

    if 'every' in time_string or 'each' in time_string:
        reminder = create_periodic_reminder(time_string, subject, separator_word, actor_id, time)

        if not isinstance(reminder, dict):
            return reminder
        msg = "I set up your reminder for every {}{}. The first one will happen on ".format(
            "{} ".format(reminder['interval']) if reminder['interval'] > 1 else "",
            unit_to_readable(reminder['unit'], reminder['interval'] == 1),
        ) + '{}'

    else:
        reminder = create_onetime_reminder(time_string, subject, separator_word, actor_id, time)
        msg = "I set up your reminder for {}"
    return reminder


def handle_button(data, **kwargs):
    db = kwargs['db']
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
            'delete': True,
        }
    if method == REMOVE_BUTTONS:
        answer = {
            'answer': get_affirmation(),
            'message': reminder_to_string(reminder),
        }
    if method == DELETE_MESSAGE:
        answer = {
            'answer': "You will be reminded.",
            'delete': True
        }
    if method == REMOVE_PERIODIC_REMINDER:
        table.delete(id=reminder_id)
        answer = {
            'answer': "Reminder deleted",
            'message': "{}\n\nThis periodic reminder was deleted.".format(reminder_to_string(reminder)),
        }
    if method in SNOOZE_REMINDERS:
        snooze = SNOOZE_REMINDERS[method]
        now = datetime.datetime.now()
        amount = snooze['amount']
        if reminder['periodic']:
            reminder = copy_periodic_to_onetime_and_rewind(reminder)
        while reminder['next'] < now:
            reminder['next'] = reminder['next'] + snooze['delta']
        reminder['active'] = True

        if 'id' in reminder:
            table.update(reminder, ['id'])
        else:
            table.insert(reminder)

        answer = {
            'answer': "Reminder snoozed for {}".format(amount),
            'delete': True,
        }
    return answer


def create_periodic_reminder(time_string, subject, separator_word, actor_id, time):
    now = time
    split_every = time_string.split("every")
    if len(split_every) <= 1:
        split_every = time_string.split("each")
    part_before = split_every[0]
    part_after = split_every[1]
    time_string_parts = part_after.split()

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

    contains_date = None
    if rest:
        contains_date = rest
    elif part_before:
        contains_date = part_before
    if contains_date:
        date_time, parsed = calendar.parseDT(contains_date, sourceTime=time)
        if parsed == 0:
            if unit == 'month':
                day = int(re.sub('\D', '', contains_date))
                if 0 < day < 29:  # sorry we can't handle february otherwise.
                    date_time = datetime.datetime(year=time.year, month=time.month, day=day, hour=7, minute=0)
                else:
                    return "Oh no, I couldn't understand what you mean by \"{}\". Note that you can only use " \
                           "dates (days of month) between 1 and 28, unfortunately.".format(contains_date)
            else:
                return "Oh no, I couldn't understand what you mean by \"{}\".".format(contains_date)

        if parsed == 1:
            date_time = datetime.datetime.combine(date_time.date(), datetime.time(hour=7, minute=0))

        if parsed == 2:
            # time without date - only makes sense if unit is day or hour:
            if unit != 'day' and unit != 'h':
                return "Oh no, I couldn't understand what you mean by \"{}\". Note that you can only set " \
                       "a time (without a weekday or date) if your reminder is every X days or hours".format(contains_date)
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
        'actor': actor_id,
    }
    present = datetime.datetime.now()
    while reminder['next'] < present:
        advance_periodic_reminder(reminder)
    return reminder


def create_onetime_reminder(time_string, subject, separator_word, actor_id, time):
    now = time
    date_time, parsed = calendar.parseDT(time_string, sourceTime=time)
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
        'actor': actor_id,
    }
    return reminder


def copy_periodic_to_onetime_and_rewind(periodic_reminder):
    if not periodic_reminder['periodic']:
        return
    unit = periodic_reminder['unit']
    interval = periodic_reminder['interval']
    onetime_reminder = {
        'next': periodic_reminder['next'],
        'subject': periodic_reminder['subject'],
        'active': periodic_reminder['active'],
        'periodic': False,
        'separator': periodic_reminder['separator'],
        'actor': periodic_reminder['actor'],
    }
    if unit == 'min':
        onetime_reminder['next'] -= datetime.timedelta(minutes=interval)
    if unit == 'h':
        onetime_reminder['next'] -= datetime.timedelta(hours=interval)
    if unit == 'day':
        onetime_reminder['next'] -= datetime.timedelta(days=interval)
    if unit == 'week':
        onetime_reminder['next'] -= datetime.timedelta(days=7*interval)
    if unit == 'month':
        onetime_reminder['next'] = advance_by_a_month(onetime_reminder['next'], -interval)
    if unit == 'year':
        dt = onetime_reminder['next']
        onetime_reminder['next'] = datetime.datetime(dt.year - interval, dt.month, dt.day, dt.hour, dt.minute)

    return onetime_reminder


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

    if params['debug']:
        logger.info("Periodic reminder advanced by {} {}, new date is {}".format(
            interval,
            unit,
            reminder['next']
        ))


def advance_by_a_month(date_time, months):

    new_month = date_time.month + months
    add_year = 0
    while new_month > 12:
        new_month -= 12
        add_year += 1

    while new_month < 1:
        new_month += 12
        add_year -= 1

    day = date_time.day

    if day > 30 and new_month not in [1, 3, 5, 7, 8, 10, 12]:
        day = 30
    if day > 28 and new_month == 2:
        day = 28  # fuck leap years

    return datetime.datetime(
        date_time.year + add_year,
        new_month,
        day,
        date_time.hour,
        date_time.minute
    )


def unit_to_readable(unit, singular=False):
    if unit == 'h':
        return 'hour' if singular else 'hours'
    if unit == 'min':
        return 'minute' if singular else 'minutes'
    return unit if singular else unit + 's'


def reminder_to_string(reminder):
    return "Remember{} {}".format(
        ' to' if 'separator' not in reminder or reminder['separator'] is None else
        reminder['separator'] if len(reminder['separator']) <= 1 else
        " {}".format(reminder['separator']),
        reminder['subject'])


def run_periodically(db):
    debug = params['debug']
    table = db['reminders']
    send = params['sendmsg']
    if debug:
        logger.info("Querying reminders...")

    now = datetime.datetime.now()
    reminders = db.query('SELECT * FROM reminders WHERE active IS TRUE AND next < :now', now=now)

    count = 0
    for reminder in reminders:
        count += 1
        if debug:
            logger.info("Sending reminder {}".format(count))
        # this is so stupid I can't even
        # dataset returns dates as string but only accepts them as datetime
        reminder['next'] = datetime.datetime.strptime(reminder['next'], '%Y-%m-%d %H:%M:%S.%f')

        msg = reminder_to_string(reminder)

        buttons = [
            [{
                'text': 'Got it!',
                'data': '{}:{}'.format(reminder['id'], REMOVE_BUTTONS),
            }],
        ]

        if reminder['periodic']:
            advance_periodic_reminder(reminder)
            buttons.append(
                [{
                    'text': "Remove this reminder",
                    'data': '{}:{}'.format(reminder['id'], REMOVE_PERIODIC_REMINDER),
                }],
            )
        else:
            reminder['active'] = False

        buttons.append([
            {
                'text': snooze['button'],
                'data': '{}:{}'.format(reminder['id'], snooze_type),
            } for snooze_type, snooze in SNOOZE_REMINDERS.items()
        ])

        send({
            'message': msg,
            'buttons': buttons,
        }, key=key, recipient_id=reminder['actor'] if 'actor' in reminder else None)

        if debug:
            logger.info("Updating reminder {}".format(count))
        table.update(reminder, ['id'])
        if debug:
            logger.info("Finished reminder {}".format(count))
    if debug:
        logger.info("Sent out {} reminders".format(count))



with open('result.json') as file:
    cont = json.load(file)

cenow = datetime.datetime.now()
params['debug'] = False
for msg in cont['messages']:
    if 'text' in msg and isinstance(msg['text'], str):
        if matches_message(msg['text']):
            reminder = handle(msg['text'], actor_id=msg['from_id'], time=msg['date'])
            if isinstance(reminder, dict):
                if reminder['next'] > cenow:
                    print(msg['date'])
                    print(msg['text'])


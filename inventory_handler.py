import re
import datetime

PLACE_PATTERN = re.compile('^\s*the\s+(.+?)\s+(is|are)\s+(.+?)\s+the\s+(.+?)\.?\s*$',
                           flags=re.I)
SEARCH_PATTERN = re.compile('^\s*where\s+(is|are)\s+the\s+(.+?)\??\s*$',
                            flags=re.I)
LIST_PATTERN = re.compile('^\s*what\s+is\s+(.+?)\s+the\s+(.+?)\??\s*$',
                          flags=re.I)


def matches_message(message):
    return PLACE_PATTERN.match(message) is not None \
           or SEARCH_PATTERN.match(message) is not None \
           or LIST_PATTERN.match(message) is not None


def handle(message, db):
    match = PLACE_PATTERN.match(message.lower())
    if match:
        return handle_place(match, db)
    match = SEARCH_PATTERN.match(message.lower())
    if match:
        return handle_search(match, db)
    match = LIST_PATTERN.match(message.lower())
    if match:
        return handle_list(match, db)
    return "Oh... uh... something went terribly wrong. I'm sorry."


def handle_button(data, db):
    table = db['inventory']
    thing = table.find_one(id=data)

    if not thing:
        return "Uh oh, something went wrong"

    table.delete(id=data)
    msg = format_thing("he {} {} no longer {} the {}.", thing)
    answer = {
        'answer': 'T{}'.format(msg),
        'message': 'Okay, t{}'.format(msg),
    }
    return answer


def handle_list(match, db):
    groups = match.groups()
    position = groups[0]
    location = groups[1]

    table = db['inventory']
    things = table.find(location=location)

    msg = ""
    for thing in things:
        msg += format_thing("The {} {} {} the {}.\n", thing)

    if not msg:
        return "There seems to be nothing {} the {}.".format(position, location)
    return msg


def handle_search(match, db):
    groups = match.groups()
    plural = groups[0]
    name = groups[1]

    table = db['inventory']
    thing = table.find_one(name=name)

    if thing:
        button_data = {
            'text': "No {} not".format("they're" if thing['plural'] else "it's"),
            'data': thing['id'],
        }
        msg = "The {} {} {} the {}.".format(thing['name'],
                                            'are' if thing['plural'] else 'is',
                                            thing['position'],
                                            thing['location'])
        ret = {
            'message': msg,
            'buttons': [[button_data]]
        }
        return ret

    else:
        return "Sorry, I don't know where the {} {}.".format(name, plural)


def handle_place(match, db):
    groups = match.groups()

    thing = groups[0]
    plural = groups[1] == 'are'
    position = groups[2]
    location = groups[3]

    new_thing = {
        'name': thing,
        'plural': plural,
        'position': position,
        'location': location,
        'timestamp': datetime.datetime.now()
    }

    table = db['inventory']

    old_thing = table.find_one(name=thing)
    table.upsert(new_thing, ['name'])

    if old_thing:
        msg = "The {} {} moved from {} the {} to {} the {}.".format(thing,
                                                                    'have' if plural else 'has',
                                                                    old_thing['position'],
                                                                    old_thing['location'],
                                                                    new_thing['position'],
                                                                    new_thing['location'])
    else:
        msg = format_thing("The {} {} now {} the {}.", new_thing)

    return msg


def format_thing(string, thing, singular='is', plural='are'):
    return string.format(
        thing['name'],
        plural if thing['plural'] else singular,
        thing['position'],
        thing['location']
    )

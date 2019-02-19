import re
import datetime

PLACE_PATTERN = re.compile('^\s*the\s+(.+?)\s+(is|are)\s+(.+?)\s+the\s+(.+?)\.?\s*$',
                           flags=re.I)
SEARCH_PATTERN = re.compile('^\s*where\s+(is|are)\s+the\s+(.+?)\??\s*$',
                            flags=re.I)


def matches_message(message):
    return PLACE_PATTERN.match(message) is not None \
           or SEARCH_PATTERN.match(message) is not None


def handle(message, db):
    match = PLACE_PATTERN.match(message.lower())
    if match:
        return handle_place(match, db)
    match = SEARCH_PATTERN.match(message.lower())
    if match:
        return handle_search(match, db)
    return "Oh... uh... something went terribly wrong. I'm sorry."


def handle_search(match, db):
    groups = match.groups()
    plural = groups[0]
    name = groups[1]

    table = db['inventory']
    thing = table.find_one(name=name)

    if thing:
        return "The {} {} {} the {}.".format(thing['name'],
                                             'are' if thing['plural'] else 'is',
                                             thing['position'],
                                             thing['location'])

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
        msg = "The {} {} now {} the {}.".format(thing,
                                                'are' if plural else 'is',
                                                position,
                                                location)

    return msg

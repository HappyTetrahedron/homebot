key = 'CHANGEME'
name = 'Unnamed Feature'


def help(permission):
    return "This feature does not yet have a help text."


def setup(config, send_message):
    pass


def teardown():
    pass


def matches_message(message):
    return False


def handle(message, **kwargs):
    pass


def handle_button(data, **kwargs):
    pass


def run_periodically(db):
    pass

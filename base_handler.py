MATCH_YUP = 'yup'
MATCH_EH = 'eh'
MATCH_NOPE = 'nope'

class BaseHandler:
    def __init__(self, config, messenger, key, name):
        self._config = config
        self._messenger = messenger
        self._debug = config['debug']
        self.key = key
        self.name = name


    def help(self, permission):
        return {
            'summary': "There is no help yet for this feature.",
            'examples': [],
        }

    def teardown(self):
        pass

    def matches_message(self, message):
        return False

    def advanced_matches_message(self, message):
        if self.matches_message(message):
            return MATCH_YUP
        return MATCH_NOPE

    def handle(self, message, **kwargs):
        pass

    def handle_button(self, data, **kwargs):
        pass

    def run_periodically(self, db):
        pass

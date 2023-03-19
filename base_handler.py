class BaseHandler:
    def __init__(self, config, messenger, key, name):
        self._config = config
        self._messenger = messenger
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

    def handle(self, message, **kwargs):
        pass

    def handle_button(self, data, **kwargs):
        pass

    def run_periodically(self, db):
        pass

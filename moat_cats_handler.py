from requests import HTTPError

from base_handler import *
import datetime
import random
import re
import requests

from utils import PERM_ADMIN

PATTERN = re.compile('^(have the cats been fed|cats|do i need to feed the cats|should i feed the cats|do the cats need (feeding|food|to be fed)|is it (din|lun)[- ]?(din|lun) time|cat food|cats fed|were the cats fed)\??$', flags=re.I)

POSITIVE_REPLIES = [
    'You should feed the cats.',
    'The cats need to be fed.',
    'It is time to feed the cats.',
    'The cats have not yet been fed.',
]
NEGATIVE_REPLIES = [
    'The cats do not need to be fed.',
    'The cats have already been fed.',
    'Do not feed the cats yet.',
    'The cats are already fed.',
    'No food for the kitties now.',
    'The cats already had food, their meow is a lie.',
]

class MoatCatsHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="moat_cats_battery", name="Cats")
        if 'moat' in config:
            self.base_url = config['moat']['base_url']
            self.enabled = True
        else:
            self.base_url = None
            self.enabled = False

    def help(self, permission):
        if not self.enabled:
            return
        if permission < PERM_ADMIN:
            return
        return {
            'summary': "Can check whether the cats need to be fed",
            'examples': ["Have the cats been fed?"],
        }

    def matches_message(self, message):
        if not self.enabled:
            return
        return PATTERN.match(message) is not None

    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        return self.check_cats()

    def check_cats(self):
        try:
            status = self._get_status()
            last_fed = datetime.datetime.strptime(status['last_feed'], "%Y-%m-%d %H:%M:%S")
            need_feeding = status['need_feeding']

            replies = POSITIVE_REPLIES if need_feeding else NEGATIVE_REPLIES
            messages = []
            try:
                messages.append("The cats have last been fed at {}".format(last_fed.strftime("%H:%M")))
            except ValueError:
                pass
            messages.append(random.choice(replies))

            return {
                'message': '\n'.join(messages),
            }
        except HTTPError:
            return {
                'message': 'Failed to check cats status :/',
                'answer': 'Error!',
            }
        except requests.exceptions.ConnectionError:
            return {
                'message': 'Failed to check cats status :/',
                'answer': 'Error!',
            }

    def _get_status(self):
        response = requests.get(f'{self.base_url}/cats-status', timeout=5)
        response.raise_for_status()
        return response.json()

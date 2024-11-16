import datetime

from dateutil import parser
import requests


class WekanService:
    def __init__(self, config):
        if 'wekan' in config:
            self.config = config['wekan']
            self.enabled = True
            self.token_expires = None
        else:
            self.enabled = False

    def can_create_cards(self, telegram_user_id):
        return self.get_wekan_user_id(telegram_user_id) is not None

    def get_wekan_user_id(self, telegram_user_id):
        wekan_user = self._get_wekan_user(telegram_user_id)
        if not wekan_user:
            return None
        return wekan_user['wekan_id']

    def get_wekan_user_name(self, telegram_user_id):
        wekan_user = self._get_wekan_user(telegram_user_id)
        if not wekan_user:
            return None
        return wekan_user['name']

    def get_cards(self, telegram_user_id, lists=None, lanes=None):
        user_id = self.get_wekan_user_id(telegram_user_id)
        if not user_id:
            return []
        valid_lists_ids = [l['id'] for l in self.config['source_lists']]

        all_lane_cards = {}
        for la in lanes:
            lane_cards = self._call_api(f"swimlanes/{la}/cards")
            lane_cards = [c for c in lane_cards if len(c['assignees']) == 0 or user_id in c['assignees']]
            for lc in lane_cards:
                if lc['listId'] in valid_lists_ids:
                    if lc['listId'] not in all_lane_cards:
                        all_lane_cards[lc['listId']] = []

                    all_lane_cards[lc['listId']].append(lc)

        all_list_cards = {}
        for li in lists:
            list_cards = self._call_api(f"lists/{li}/cards")
            list_cards = [c for c in list_cards if len(c['assignees']) == 0 or user_id in c['assignees']]
            if len(list_cards) != 0:
                all_list_cards[li] = list_cards

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
        return cards

    def create_card(self, telegram_user_id, title, list_id=None, assign_to_creator=False):
        user_id = self.get_wekan_user_id(telegram_user_id)
        if not user_id:
            return None
        if list_id is None:
            list_id = self.config['default_list']
        payload = {
            "authorId": user_id,
            "title": title,
            "swimlaneId": self.config['default_lane']
        }
        if assign_to_creator:
            payload['assignees'] = [user_id]
        card = self._call_api(f'lists/{list_id}/cards', payload=payload)
        return card['_id']

    def move_card_to_done(self, list_id, card_id):
        if not self.enabled:
            return
        payload = {
            'listId': self.config['target_list']
        }
        self._call_api(f'lists/{list_id}/cards/{card_id}', payload, method='PUT')

    def move_card_to_in_progress(self, list_id, card_id):
        if not self.enabled:
            return
        payload = {
            'listId': self.config['inprogress_list']
        }
        self._call_api(f'lists/{list_id}/cards/{card_id}', payload,method='PUT')

    def move_card_to_backlog(self, list_id, card_id, start_date: datetime.datetime):
        if not self.enabled:
            return
        payload = {
            'listId': self.config['backlog_list'],
            'startAt': start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        self._call_api(f'lists/{list_id}/cards/{card_id}', payload, method='PUT')

    def assign_card(self, list_id, card_id, telegram_user_id):
        user_id = self.get_wekan_user_id(telegram_user_id)
        if not user_id:
            return
        data = {
            '_id': card_id,
            'assignees': [user_id],
        }
        self._call_api(f'lists/{list_id}/cards/{card_id}', data, method='PUT')

    def _get_wekan_user(self, telegram_user_id):
        if not self.enabled:
            return None
        wekan_user = [u for u in self.config['users'] if u['telegram_id'] == telegram_user_id]
        if len(wekan_user) != 1:
            return None
        return wekan_user[0]

    def _call_api(self, path, payload=None, method='GET'):
        base_url = self.config['url']
        if not self._token_valid():
            self._login()
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        url = f'{base_url}/api/boards/{self.config['board']}/{path}'
        if payload:
            if method == 'GET':
                method = 'POST'
            data = requests.request(method, url, json=payload, headers=headers)
        else:
            data = requests.get(url, headers=headers)
        return data.json()

    def _token_valid(self):
        return self.token_expires and self.token_expires > datetime.datetime.now().astimezone()

    def _login(self):
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

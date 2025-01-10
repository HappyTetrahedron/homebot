import requests


class ButtonhubService:

    def __init__(self, config):
        if 'buttonhub' in config:
            self.config = config['buttonhub']
            self.base_url = config['buttonhub']['base_url']
            self.enabled = True
        else:
            self.config = {}
            self.enabled = False

    def get_state(self):
        try:
            response = requests.get(f'{self.base_url}/state', timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError:
            raise ButtonhubError
        except requests.exceptions.ConnectionError:
            raise ButtonhubError

    def run_flow(self, flow_name):
        try:
            url = '{}/flows/{}'.format(self.base_url, flow_name)
            response = requests.post(url, timeout=5)
            response.raise_for_status()
        except requests.HTTPError:
            raise ButtonhubError
        except requests.exceptions.ConnectionError:
            raise ButtonhubError

    def get_flows(self):
        try:
            url = '{}/flows'.format(self.base_url)
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()['flows']
        except requests.HTTPError:
            raise ButtonhubError
        except requests.exceptions.ConnectionError:
            raise ButtonhubError

class ButtonhubError(RuntimeError):
    pass

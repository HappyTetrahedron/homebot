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

    def get_config(self, name):
        self.config.get(name) or {}

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
            response = requests.post(f'{self.base_url}/flows/{flow_name}', timeout=5)
            response.raise_for_status()
        except requests.HTTPError:
            raise ButtonhubError
        except requests.exceptions.ConnectionError:
            raise ButtonhubError

    def get_flows(self):
        try:
            response = requests.get(f'{self.base_url}/flows', timeout=5)
            response.raise_for_status()
            return response.json()['flows']
        except requests.HTTPError:
            raise ButtonhubError
        except requests.exceptions.ConnectionError:
            raise ButtonhubError

class ButtonhubError(RuntimeError):
    pass

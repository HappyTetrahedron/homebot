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
        response = requests.get(f'{self.base_url}/state', timeout=5)
        response.raise_for_status()
        return response.json()

    def run_flow(self, flow_name):
        url = '{}/flows/{}'.format(self.base_url, flow_name)
        response = requests.post(url, timeout=5)
        response.raise_for_status()

    def get_flows(self):
        url = '{}/flows'.format(self.base_url)
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()['flows']

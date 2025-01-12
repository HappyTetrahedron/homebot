import requests


class MoatService:

    def __init__(self, config):
        if 'moat' in config:
            self.base_url = config['moat']['base_url']
            self.enabled = True
        else:
            self.enabled = False

    def get_cats_status(self):
        try:
            response = requests.get(f'{self.base_url}/cats-status', timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError:
            raise MoatError
        except requests.exceptions.ConnectionError:
            raise MoatError

class MoatError(RuntimeError):
    pass

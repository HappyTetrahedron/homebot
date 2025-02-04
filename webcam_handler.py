from base_handler import *
import requests
from utils import PERM_ADMIN, get_timestamp
from utils import get_exclamation
from PIL import Image

UPDATE = 'UP'
NOIMAGE = 'noimage.png'

class WebcamHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="webcam", name="Webcams")
        if 'webcam' in config:
            self.cams = config['webcam'].get('cams', [])
            self.tmp_path = config['webcam'].get('tmp_path', '/tmp/campic.jpg')
            self.enabled = True
        else:
            self.enabled = False

    def matches_message(self, message):
        if not self.enabled:
            return False
        if message.lower().startswith('show '):
            l = message[5:].lower()
            return any([any([l.startswith(prefix) for prefix in x['prefices']])
                        for x in self.cams])

    def help(self, permission):
        if not self.enabled:
            return
        if permission >= PERM_ADMIN:
            return {
                'summary': "Shows you snapshots from your webcam feeds",
                'examples': ["show living room"],
            }

    def handle(self, message, **kwargs):
        l = message[5:].lower()
        for cam in self.cams:
            for prefix in cam['prefices']:
                if l.startswith(prefix):
                    if ('users' in cam and str(kwargs['actor_id']) in cam['users']) \
                        or ('users' not in cam and kwargs['permission'] >= PERM_ADMIN):
                        return self.get_snapshot(cam['name'])
                    else:
                        return "Sorry, you don't get to see this camera."
        return "Whoopsie, this never happens"

    def handle_button(self, data, **kwargs):
        data = data.split('§', 1)
        cmd = data[0]

        if cmd == UPDATE:
            resp = self.get_snapshot(data[1], include_timestamp=True)
            resp['answer'] = "Updated!"
            return resp

    def get_snapshot(self, cam, include_timestamp=False):
        buttons = [[{
                'text': "Update",
                'data': "{}§{}".format(UPDATE, cam)
            }]]
        try:
            url = next(c['url'] for c in self.cams if c['name'] == cam)
            resp = requests.get(url, timeout=8)
            with open("{}.jpg".format(self.tmp_path), 'wb') as file:
                file.write(resp.content)
            im = Image.open("{}.jpg".format(self.tmp_path))
            im.save("{}.png".format(self.tmp_path))

            message = f'{cam} camera'
            if include_timestamp:
                message = f'{message} ({get_timestamp()})'

            return {
                'message': message,
                'photo': f'{self.tmp_path}.png',
                'buttons': buttons,
            }
        except requests.exceptions.ConnectionError:
            return {
                'photo': NOIMAGE,
                'message': "{} Seems like the {} webcam isn't online. :(".format(get_exclamation(), cam),
                'buttons': buttons,
            }
        except StopIteration:
            return {
                'photo': NOIMAGE,
                'message': "{} Seems like this webcam doesn't exist anymore. :(".format(get_exclamation()),
            }
        except requests.exceptions.Timeout:
            return {
                'photo': NOIMAGE,
                'message': "{} The {} webcam timed out. :(".format(get_exclamation(), cam),
                'buttons': buttons,
            }
        except Exception as e:
            print(e)
            return {
                'photo': NOIMAGE,
                'message': "{} Something went horribly wrong with {} webcam. :(".format(get_exclamation(), cam),
                'buttons': buttons,
            }

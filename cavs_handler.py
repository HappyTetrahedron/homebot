from base_handler import *
import subprocess

from utils import PERM_ADMIN

class CavsHandler(BaseHandler):

    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="cavs", name="Initialize CAVS")
        if 'cavs_init_command' in config:
            self.cmd = config['cavs_init_command']
            self.enabled = True
        else:
            self.cmd = None
            self.enabled = False

    def help(self, permission):
        if not self.enabled:
            return
        if permission >= PERM_ADMIN:
            return {
                'summary': "Initializes the CAVS.",
                'examples': ["initialize cavs"],
            }

    def matches_message(self, message):
        if not self.enabled:
            return
        return message.lower().startswith('init') and 'cavs' in message.lower()


    def handle(self, message, **kwargs):
        if kwargs['permission'] < PERM_ADMIN:
            return "Sorry, you can't do this."
        self._messenger.send_message("All right, give me a second...")
        status, out, err = self.run_command(self.cmd)
        if status == 0:
            return "The CAVS are initialized."
        return "There seems to have been an issue: \n{}".format(err)


    def run_command(self, command):
        process = subprocess.run(
            command,
            capture_output=True,
            shell=True
        )
        out = process.stdout
        err = process.stderr
        status = process.returncode
        return status, out.decode('UTF-8'), err.decode('UTF-8')

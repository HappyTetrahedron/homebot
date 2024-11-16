from base_handler import *
import subprocess
import json
import time
import requests
from utils import PERM_OWNER

SHUT_DOWN = "bye"
TURN_ON = "on"
TURN_POWER_OFF = "off"
REMOVE_BUTTONS = "rm"

class PCHandler(BaseHandler):
    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key= "pc", name="Computer Control")
        if 'pc' in config:
            self.config = config['pc']
            self.enabled = True
        else:
            self.enabled = False

    def matches_message(self, message):
        if not self.enabled:
            return False
        return message.lower().startswith('pc')

    def help(self, permission):
        if not self.enabled:
            return
        if permission >= PERM_OWNER:
            return {
                'summary': "Can turn your PC on and off",
                'examples': ["PC"],
            }

    def handle(self, message, **kwargs):
        if kwargs['permission'] != PERM_OWNER:
            return "Nuh-uh, you can't do this"

        if self.is_on():
            return {
                "message": "PC is on. \n\n{}".format(self.get_workspaces()),
                'buttons': [
                    [{
                        'text': "Shut it down!",
                        'data': "{}".format(SHUT_DOWN)
                    }],
                    [{
                        'text': "kthx",
                        'data': "{}".format(REMOVE_BUTTONS)
                    }],
                ],
            }
        if self.is_powered():
            return {
                "message": "PC is off but powered",
                'buttons': [
                    [{
                        'text': "Turn off power",
                        'data': "{}".format(TURN_POWER_OFF)
                    }],
                    [{
                        'text': "Boot it up",
                        'data': "{}".format(TURN_ON)
                    }],
                    [{
                        'text': "kthx",
                        'data': "{}".format(REMOVE_BUTTONS)
                    }],
                ],
            }
        return {
            "message": "PC is off",
            'buttons': [
                [{
                    'text': "Boot it up",
                    'data': "{}".format(TURN_ON)
                }],
                [{
                    'text': "kthx",
                    'data': "{}".format(REMOVE_BUTTONS)
                }],
            ],
        }


    def handle_button(self, data, **kwargs):
        if kwargs['permission'] != PERM_OWNER:
            return "Nuh-uh, you can't do this"
        data = data.split(':')
        cmd = data[0]

        if cmd == SHUT_DOWN:
            return self.shut_down()
        if cmd == TURN_POWER_OFF:
            return {
                "message": self.turn_power_off(),
                "answer": "Gotcha!",
            }
        if cmd == TURN_ON:
            return {
                "message": self.turn_on(),
                "answer": "Gotcha!",
            }
        if cmd == REMOVE_BUTTONS:
            if self.is_on():
                return {
                    "message": "PC is on. \n\n{}".format(self.get_workspaces()),
                    "answer": "Gotcha!",
                }
            if self.is_powered():
                return {
                    "message": "PC is off but powered",
                    "answer": "Gotcha!",
                }
            return {
                "message": "PC is off",
                "answer": "Gotcha!",
            }


    def get_workspaces(self):
        status, out, err = self.run_command("sudo ./getworkspaces")
        if status != 0:
            return "Error when getting workspace info: \n{}".format(err)

        tree = json.loads(out)

        monitors = [node for node in tree['nodes'] if not node['name'].startswith("__")]
        workspaces = []
        for monitor in monitors:
            for subnode in monitor['nodes']:
                if subnode['name'] == 'content':
                    workspaces = workspaces + subnode['nodes']

        def get_all_leaf_names(node):
            if len(node['nodes']) == 0:
                return node['name']
            myname = ""
            for subnode in node['nodes']:
                myname += "{}, ".format(get_all_leaf_names(subnode))
            return myname[:-2]

        msg = ""
        for workspace in workspaces:
            msg += "Workspace {}:\n".format(workspace['name'])
            msg += "{}\n\n".format(get_all_leaf_names(workspace))

        return msg


    def shut_down(self):
        status, out, err = self.run_command("sudo ./shutdown")
        if status == 0:
            return {
                "message": "Your PC is now shutting down.",
                'buttons': [
                    [{
                        'text': "Turn off power",
                        'data': "{}".format(TURN_POWER_OFF)
                    }],
                    [{
                        'text': "Boot it back up",
                        'data': "{}".format(TURN_ON)
                    }],
                    [{
                        'text': "kthx",
                        'data': "{}".format(REMOVE_BUTTONS)
                    }],
                ],
            }
        else:
            return "There was some issue when trying to shut down your PC."


    def turn_power_off(self, force=False):
        if not force:
            if self.is_on():
                return "Your PC is on. I won't cut power."
        response = requests.get("{}/relay?state=0".format(self.config['switch_ip']))
        if response.status_code == 200:
            return "Alright, I turned off your PC's power."
        return "I wasn't able to turn off your PC's power, sorry :("


    def turn_on(self, force=False):
        if not force:
            if self.is_on():
                return "Your PC is already on. I won't cycle power."

        if self.is_powered():
            response = requests.get("{}/relay?state=0".format(self.config['switch_ip']))
            if response.status_code != 200:
                return "I wasn't able to cycle power, sorry :("
            time.sleep(2)

        response = requests.get("{}/relay?state=1".format(self.config['switch_ip']))
        if response.status_code != 200:
            return "I wasn't able to turn on your PC, sorry :("
        return "Your PC should now be turning on."


    def is_powered(self):
        status = json.loads(requests.get("{}/report".format(self.config['switch_ip'])).text)
        return status['relay']


    def is_on(self):
        status, out, err = self.run_command("echo love")
        return status == 0


    def run_command(self, command):
        cmd = self.gen_command(command)
        process = subprocess.run(
            cmd,
            capture_output=True,
            shell=True
        )
        out = process.stdout
        err = process.stderr
        status = process.returncode
        return status, out.decode('UTF-8'), err.decode('UTF-8')


    def gen_command(self, command):
        return "ssh {}@{} -i {} '{}'".format(
            self.config['user'],
            self.config['host'],
            self.config['keyfile'],
            command
        )

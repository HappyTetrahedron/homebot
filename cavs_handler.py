from base_handler import *
import subprocess

key = "cavs"

params = {}


def setup(config, send_message):
    params['cmd'] = config['cavs_init_command']


def matches_message(message):
    return message.lower().startswith('init') and 'cavs' in message.lower()


def handle(message, **kwargs):
    status, out, err = run_command(params["cmd"])
    if status == 0:
        return "Alright, the CAVS are initialized"
    return "There seems to have been an issue: \n{}".format(err)


def run_command(command):
    process = subprocess.run(
        command,
        capture_output=True,
        shell=True
    )
    out = process.stdout
    err = process.stderr
    status = process.returncode
    return status, out.decode('UTF-8'), err.decode('UTF-8')


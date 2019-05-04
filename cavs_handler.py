from base_handler import *
import subprocess

key = "cavs"

params = {}


def setup(config, send_message):
    params['cmd'] = config['cavs_init_command']
    params['sendmsg'] = send_message


def matches_message(message):
    return message.lower().startswith('init') and 'cavs' in message.lower()


def handle(message, **kwargs):
    params['sendmsg']("All right, give me a second...")
    status, out, err = run_command(params["cmd"])
    if status == 0:
        return "The CAVS are initialized."
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


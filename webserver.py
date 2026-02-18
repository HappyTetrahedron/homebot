from flask import Flask
from flask import request
import asyncio

app = Flask(__name__)

params = {}


def init(send_message_to_all_admins, config):
    params['send'] = send_message_to_all_admins
    params['config'] = config

def run():
    app.run(params['config']['host'], params['config']['port'])


@app.route("/send", methods=['POST'])
def forward_message():
    data = request.get_json(force=True)
    message = data['message']
    params['send'](message)
    return ""

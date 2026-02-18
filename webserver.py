from flask import Flask
from flask import request
import asyncio

app = Flask(__name__)

params = {}


def init(send_message_to_all_admins, config, loop):
    params['send'] = send_message_to_all_admins
    params['config'] = config
    params['loop'] = loop


def run():
    app.run(params['config']['host'], params['config']['port'])


@app.route("/send", methods=['POST'])
def forward_message():
    data = request.get_json(force=True)
    message = data['message']
    future = asyncio.run_coroutine_threadsafe(params['send'](message), params['loop'])
    future.result()
    return ""

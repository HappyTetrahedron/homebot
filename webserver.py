from flask import Flask
from flask import request

app = Flask(__name__)

params = {}


def init(bot, config):
    params['bot'] = bot
    params['config'] = config


def run():
    app.run(params['config']['host'], params['config']['port'])


@app.route("/send", methods=['POST'])
def forward_message():
    data = request.get_json()
    message = data['message']

    params['bot'].send_message(params['config']['owner_id'], message)
    return ""

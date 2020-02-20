from flask import Flask
from flask import request

app = Flask(__name__)

params = {}


def init(sendmessage, config):
    params['send'] = sendmessage
    params['config'] = config


def run():
    app.run(params['config']['host'], params['config']['port'])


@app.route("/send", methods=['POST'])
def forward_message():
    data = request.get_json(force=True)
    message = data['message']
    params['send'](message)
    return ""

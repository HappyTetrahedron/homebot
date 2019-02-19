#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random
import yaml
import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler
import webserver
import dataset

import inventory_handler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

AFFIRMATIONS = [
    "Cool",
    "Nice",
    "Doing great",
    "Awesome",
    "Okey dokey",
    "Neat",
    "Whoo",
    "Wonderful",
    "Splendid",
]

HANDLERS = {
    'inv': inventory_handler,
}


class PollBot:
    def __init__(self):
        self.db = None
        self.config = None

    @staticmethod
    def get_affirmation():
        return random.choice(AFFIRMATIONS)

    @staticmethod
    def assemble_inline_buttons(button_data, prefix_key):
        buttons = []
        for row_data in button_data:
            row = []
            for button_data in row_data:
                button = InlineKeyboardButton(button_data['text'],
                                              callback_data='{}#{}'.format(
                                                  prefix_key,
                                                  button_data['data']
                                              ))
                row.append(button)
            buttons.append(row)
        return InlineKeyboardMarkup(buttons)

    def handle_message(self, bot, update):
        if str(update.message.from_user.id) != str(self.config['owner_id']):
            print(update.message.from_user.id)
            print(self.config['owner_id'])
            update.message.reply_text("You're not my master. I won't talk to you!")
            return
        for key, handler in HANDLERS.items():
            if handler.matches_message(update.message.text):
                reply = handler.handle(update.message.text, self.db)
                if not isinstance(reply, dict):
                    update.message.reply_text(reply)
                else:
                    buttons = None
                    if 'buttons' in reply:
                        buttons = self.assemble_inline_buttons(reply['buttons'], key)
                    update.message.reply_text(reply['message'], reply_markup=buttons)
                return

        update.message.reply_text(self.get_affirmation())

    def handle_inline_button(self, bot, update):
        query = update.callback_query
        data = update.callback_query.data
        data = data.split('#', 1)

        if len(data) < 2:
            query.answer("Something's wrong with this button.")
            return

        key = data[0]
        payload = data[1]
        if key not in HANDLERS:
            query.answer("Something's wrong with this button.")
            return

        answer = HANDLERS[key].handle_button(payload, self.db)
        if isinstance(answer, dict):
            if 'message' in answer:
                buttons = None
                if 'buttons' in answer:
                    buttons = self.assemble_inline_buttons(answer['buttons'], key)
                bot.edit_message_text(
                    text=answer['message'],
                    reply_markup=buttons,
                    chat_id=query.message.chat.id,
                    message_id=query.message.message_id
                )
            query.answer(answer['answer'])
        else:
            query.answer(answer)

    # Help command handler
    @staticmethod
    def handle_help(bot, update):
        """Send a message when the command /help is issued."""
        helptext = "I am HappyTetrahedron's personal butler.\n\b" \
                   "If you are not HappyTetrahedron, I fear I won't be useful to you."

        update.message.reply_text(helptext, parse_mode="Markdown")

    # Error handler
    @staticmethod
    def handle_error(bot, update, error):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, error)

    def run(self, opts):
        with open(opts.config, 'r') as configfile:
            config = yaml.load(configfile)

        self.db = dataset.connect('sqlite:///{}'.format(config['db']))
        self.config = config

        """Start the bot."""
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(config['token'])

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("help", self.handle_help))

        dp.add_error_handler(self.handle_error)

        # Callback queries from button presses
        dp.add_handler(CallbackQueryHandler(self.handle_inline_button))

        dp.add_handler(MessageHandler(None, self.handle_message))

        # Start the Bot
        updater.start_polling()

        webserver.init(updater.bot, config)
        webserver.run()

        updater.idle()


def main(opts):
    PollBot().run(opts)


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-c', '--config', dest='config', default='config.yml', type='string',
                      help="Path of configuration file")
    (opts, args) = parser.parse_args()
    main(opts)

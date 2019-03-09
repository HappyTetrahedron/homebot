#!/usr/bin/env python
# -*- coding: utf-8 -*-
import yaml
import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler
import webserver
import dataset

import inventory_handler
import reminder_handler
import hue_handler
import grocery_handler
import weather_handler
import trains_handler

from utils import get_affirmation, get_generic_response


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

HANDLERS = {
    inventory_handler.key: inventory_handler,
    reminder_handler.key: reminder_handler,
    hue_handler.key: hue_handler,
    grocery_handler.key: grocery_handler,
    weather_handler.key: weather_handler,
    trains_handler.key: trains_handler,
}


class PollBot:
    def __init__(self):
        self.db = None
        self.config = None
        self.bot = None

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

    def send_message(self, message, key=None):
        if isinstance(message, dict):
            buttons = None
            if 'buttons' in message:
                if not key:
                    raise ValueError("Using inline buttons requires you to pass a key")
                buttons = self.assemble_inline_buttons(message['buttons'], key)
            if 'photo' in message:
                self.bot.send_photo(self.config['owner_id'],
                                    open(message['photo'], 'rb'),
                                    caption=message.get('message'),
                                    reply_markup=buttons,
                                    parse_mode=message.get('parse_mode'))
            else:
                self.bot.send_message(self.config['owner_id'],
                                      message['message'],
                                      reply_markup=buttons,
                                      parse_mode=message.get('parse_mode'))
        else:
            self.bot.send_message(self.config['owner_id'], message)

    def handle_message(self, bot, update):
        if str(update.message.from_user.id) != str(self.config['owner_id']):
            print(update.message.from_user.id)
            print(self.config['owner_id'])
            update.message.reply_text("You're not my master. I won't talk to you!")
            return
        for key, handler in HANDLERS.items():
            if handler.matches_message(update.message.text):
                reply = handler.handle(update.message.text, self.db)
                self.send_message(reply, handler.key)
                return

        update.message.reply_text(get_generic_response())

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
                if 'photo' in answer:
                    bot.edit_message_media(
                        chat_id=query.message.chat.id,
                        message_id=query.message.message_id,
                        reply_markup=buttons,
                        media=InputMediaPhoto(
                            open(answer['photo'], 'rb'),
                            caption=answer.get('message'),
                            parse_mode=answer.get('parse_mode')
                        )
                    )
                else:
                    bot.edit_message_text(
                        text=answer['message'],
                        reply_markup=buttons,
                        chat_id=query.message.chat.id,
                        message_id=query.message.message_id,
                        parse_mode=answer.get('parse_mode')
                    )
            if 'delete' in answer and answer['delete']:
                bot.delete_message(
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
        if 'debug' not in config:
            config['debug'] = False
        if config['debug']:
            logger.info("Debug mode is ON")

        """Start the bot."""
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(config['token'])
        self.bot = updater.bot

        """Set up handlers"""
        for handler in HANDLERS.values():
            handler.setup(self.config, self.send_message)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("help", self.handle_help))

        dp.add_error_handler(self.handle_error)

        # Callback queries from button presses
        dp.add_handler(CallbackQueryHandler(self.handle_inline_button))

        dp.add_handler(MessageHandler(None, self.handle_message))

        # Start the Bot
        updater.start_polling()

        webserver.init(self.send_message, self.config)
        webserver.run()

        updater.idle()

        for handler in HANDLERS.values():
            handler.teardown()


def main(opts):
    PollBot().run(opts)


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-c', '--config', dest='config', default='config.yml', type='string',
                      help="Path of configuration file")
    (opts, args) = parser.parse_args()
    main(opts)

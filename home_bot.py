#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random
import yaml
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler
import webserver

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


class PollBot:

    def get_affirmation(self):
        return random.choice(AFFIRMATIONS)

    def handle_message(self, bot, update):
        print(update.message.from_user.id)
        print(update.message.chat.id)
        update.message.reply_text(self.get_affirmation())

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

        """Start the bot."""
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(config['token'])

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("help", self.handle_help))

        dp.add_error_handler(self.handle_error)

        dp.add_handler(MessageHandler(None, self.handle_message))

        # Start the Bot
        updater.start_polling()

        webserver.init(updater.bot, config)
        webserver.run()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading

import yaml
import datetime
import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.error import BadRequest
import webserver
import dataset

import inventory_handler
import reminder_handler
import hue_handler
import grocery_handler
import weather_handler
import trains_handler
import pc_handler
import cavs_handler
import webcam_handler
import dice_handler
import buttonhub_flows_handler
import buttonhub_battery_handler
import buttonhub_lights_handler
import buttonhub_climate_handler
import moat_cats_handler
import list_preset_handler
import wekan_handler
from base_handler import MATCH_YUP, MATCH_EH

from utils import get_generic_response
from utils import PERMISSIONS, PERM_ADMIN, PERM_OWNER, PERM_USER


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

HANDLER_CLASSES = [
    grocery_handler.GroceryHandler,
    cavs_handler.CavsHandler,
    dice_handler.DiceHandler,
    buttonhub_flows_handler.ButtonhubFlowsHandler,
    buttonhub_battery_handler.ButtonhubBatteryHandler,
    buttonhub_lights_handler.ButtonhubLightsHandler,
    buttonhub_climate_handler.ButtonhubClimateHandler,
    moat_cats_handler.MoatCatsHandler,
    hue_handler.HueHandler,
    inventory_handler.InventoryHandler,
    list_preset_handler.ListPresetHandler,
    pc_handler.PCHandler,
    reminder_handler.ReminderHandler,
    trains_handler.TrainsHandler,
    weather_handler.WeatherHandler,
    webcam_handler.WebcamHandler,
    wekan_handler.WekanHandler,
]

class HomeBot:
    def __init__(self):
        self.db = None
        self.periodic_db = None
        self.config = None
        self.bot = None
        self.exit = threading.Event()
        self.handlers = []

    def get_permissions(self, user_id):
        permission = None
        if str(user_id) == str(self.config['owner_id']):
            permission = PERM_OWNER
        if str(user_id) in self.config['admin_ids']:
            permission = PERM_ADMIN
        if str(user_id) in self.config['user_ids']:
            permission = PERM_USER
        return permission

    @staticmethod
    def assemble_inline_buttons(button_data, prefix_key):
        buttons = []
        for row_data in button_data:
            row = []
            for button_data in row_data:
                button = InlineKeyboardButton(
                    button_data['text'],
                    callback_data='{}#{}'.format(
                        prefix_key,
                        button_data['data']
                    ),
                )
                row.append(button)
            buttons.append(row)
        return InlineKeyboardMarkup(buttons)

    def send_message(self, message, key=None, update_message_id=None, recipient_id=None):
        if recipient_id is None:
            recipient_id = self.config['owner_id']
        if isinstance(message, dict):
            buttons = None
            if message.get('buttons'):
                if not key:
                    raise ValueError("Using inline buttons requires you to pass a key")
                buttons = self.assemble_inline_buttons(message['buttons'], key)
            if 'photo' in message:
                if update_message_id is not None:
                    self.bot.edit_message_media(
                        chat_id=recipient_id,
                        message_id=update_message_id,
                        reply_markup=buttons,
                        media=InputMediaPhoto(
                            open(message['photo'], 'rb'),
                            caption=message.get('message'),
                            parse_mode=message.get('parse_mode')
                        )
                    )
                else:  # new photo
                    self.bot.send_photo(recipient_id,
                                        open(message['photo'], 'rb'),
                                        caption=message.get('message'),
                                        reply_markup=buttons,
                                        parse_mode=message.get('parse_mode'))
            else:
                if update_message_id is not None:
                    self.bot.edit_message_text(
                        text=message['message'],
                        reply_markup=buttons,
                        chat_id=recipient_id,
                        message_id=update_message_id,
                        parse_mode=message.get('parse_mode')
                    )
                else:
                    self.bot.send_message(recipient_id,
                                          message['message'],
                                          reply_markup=buttons,
                                          parse_mode=message.get('parse_mode'))
        else:
            if update_message_id is not None:
                self.bot.edit_message_text(
                    text=message,
                    chat_id=recipient_id,
                    message_id=update_message_id
                )
            else:
                self.bot.send_message(recipient_id, message)

    def handle_message(self, update, context):
        permission = self.get_permissions(update.message.from_user.id)
        if self.config['debug']:
            logger.info("Received message from {}".format(update.message.from_user.id))
        if permission not in PERMISSIONS:
            update.message.reply_text("You're not my master. I won't talk to you!")
            return

        best_handler = None
        for handler in self.handlers:
            if update.message.text is not None:
                match = handler.advanced_matches_message(update.message.text)
                if match == MATCH_YUP:
                    best_handler = handler
                    break
                if match == MATCH_EH:
                    if best_handler is None:
                        best_handler = handler
                    else:
                        best_handler = None
                        break

        if best_handler:
            reply = best_handler.handle(
                update.message.text,
                db=self.db,
                message_id=update.message.message_id,
                actor_id=update.message.from_user.id,
                permission=permission,
            )
            self.send_message(reply, best_handler.key, recipient_id=update.message.from_user.id)
        else:
            update.message.reply_text(get_generic_response())

    def handle_inline_button(self, update, context):
        query = update.callback_query
        data = update.callback_query.data

        permission = self.get_permissions(query.message.chat.id)
        if permission not in PERMISSIONS:
            return

        data = data.split('#', 1)

        if len(data) < 2:
            query.answer("Something's wrong with this button.")
            return

        key = data[0]
        payload = data[1]

        for handler in self.handlers:
            if handler.key == key:
                answer = handler.handle_button(
                    payload,
                    db=self.db,
                    message_id=query.message.message_id,
                    actor_id=query.message.chat.id,
                    permission=permission
                )
                if isinstance(answer, dict):
                    if 'message' in answer or 'photo' in answer:
                        buttons = None
                        if answer.get('buttons'):
                            buttons = self.assemble_inline_buttons(answer['buttons'], key)
                        if 'photo' in answer:
                            context.bot.edit_message_media(
                                chat_id=query.message.chat.id,
                                message_id=query.message.message_id,
                                reply_markup=buttons,
                                media=InputMediaPhoto(
                                    open(answer['photo'], 'rb'),
                                    caption=answer.get('message', None),
                                    parse_mode=answer.get('parse_mode')
                                )
                            )
                        else:
                            try:
                                context.bot.edit_message_text(
                                    text=answer['message'],
                                    reply_markup=buttons,
                                    chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    parse_mode=answer.get('parse_mode')
                                )
                            except BadRequest as err: # Ignore "message is not modified"
                                if "Message is not modified" not in err.message:
                                    raise err
                    if 'delete' in answer and answer['delete']:
                        context.bot.delete_message(
                            chat_id=query.message.chat.id,
                            message_id=query.message.message_id
                        )
                    query.answer(answer['answer'])
                else:
                    query.answer(answer)

    # Help command handler
    def handle_help(self, update, context):
        """Send a message when the command /help is issued."""
        helptext = "I am HappyTetrahedron's personal butler.\n\b" \
                   "If you are not HappyTetrahedron, I fear I won't be useful to you."

        permission = self.get_permissions(update.message.from_user.id)

        if permission not in PERMISSIONS:
            update.message.reply_text(helptext, parse_mode="Markdown")
            return

        helptext = "I am HappyTetrahedron's personal butler.\n\n"
        for handler in self.handlers:
            handler_help = handler.help(permission)
            if handler_help:
                helptext += "*{}:*\n".format(handler.name)
                helptext += "{}\n".format(handler_help['summary'])
                for example in handler_help['examples']:
                    helptext += " _{}_\n".format(example)
                helptext += "\n"

        update.message.reply_text(helptext, parse_mode="Markdown")

    # Error handler
    def handle_error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)
        if self.config['debug']:
            import traceback
            traceback.print_exception(context.error)

    def run(self, opts):
        with open(opts.config, 'r') as configfile:
            config = yaml.load(configfile, Loader=yaml.SafeLoader)

        self.db = dataset.connect('sqlite:///{}'.format(config['db']))
        self.periodic_db = dataset.connect('sqlite:///{}'.format(config['db']))
        self.config = config
        if 'debug' not in config:
            config['debug'] = False
        if config['debug']:
            logger.info("Debug mode is ON")

        """Start the bot."""
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(config['token'], use_context=True)
        self.bot = updater.bot

        """Set up handlers"""
        for handler_class in HANDLER_CLASSES:
            handler = handler_class(self.config, self)
            self.handlers.append(handler)

        t = threading.Thread(target=self.scheduler_run)
        t.start()

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

        self.exit.set()

        for handler in self.handlers:
            handler.teardown()

    def scheduler_run(self):
        while not self.exit.is_set():
            for handler in self.handlers:
                try:
                    handler.run_periodically(self.periodic_db)
                except Exception as e:
                    logger.error("Exception on scheduler thread with handler {}".format(handler.key))
                    logger.exception(e)
            if datetime.datetime.now().minute == 0:
                try:
                    r = self.periodic_db.query("PRAGMA main.wal_checkpoint(FULL);")
                    if self.config['debug']:
                        for row in r:
                            logger.info("WAL checkpoint: busy flag {}, {} logged to WAL, {} checkpointed.".format(row['busy'], row['log'], row['checkpointed']))
                except Exception as e:
                    logger.error("Exception on scheduler thread during WAL checkpoint")
                    logger.exception(e)
            try:
                self.exit.wait(60)
            except Exception as e:
                logger.error("Exception on scheduler thread")
                logger.exception(e)
        logger.info("Scheduler thread has exited")
        logger.info("Exit signal is {}".format(self.exit.is_set()))


def main(opts):
    HomeBot().run(opts)


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-c', '--config', dest='config', default='config.yml', type='string',
                      help="Path of configuration file")
    (opts, args) = parser.parse_args()
    main(opts)

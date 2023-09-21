#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading

import yaml
import logging

from rocketchat_bot_sdk import RocketchatBot
from rocketchat_bot_sdk import CommandHandler
from rocketchat_bot_sdk import MessageHandler
from rocketchat_bot_sdk import ReactionHandler

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
import buttonhub_handler
import list_preset_handler
import wekan_handler

from utils import get_affirmation, get_generic_response
from utils import PERMISSIONS, PERM_ADMIN, PERM_OWNER, PERM_USER

REACTION_EMOJI = [
    ':one:',
    ':two:',
    ':three:',
    ':four:',
    ':five:',
    ':six:',
    ':seven:',
    ':eight:',
    ':nine',
    ':keycap_ten:',
    ':digit_one:',
    ':digit_two:',
    ':digit_three:',
    ':digit_four:',
    ':digit_five:',
    ':digit_six:',
    ':digit_seven:',
    ':digit_eight:',
    ':digit_nine:',
    ':digit_zero:',
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

HANDLER_CLASSES = [
    dice_handler.DiceHandler,
    reminder_handler.ReminderHandler,
    trains_handler.TrainsHandler,
    weather_handler.WeatherHandler,
]

class RcHomeBot:
    def __init__(self):
        self.db = None
        self.periodic_db = None
        self.config = None
        self.bot = None
        self.exit = threading.Event()
        self.handlers = []

    def get_permissions(self, user_id):
        # Permission handling not useful in this use case
        return PERM_USER

    @staticmethod
    def assemble_inline_buttons(button_data, prefix_key):
        button_descriptions =  []
        button_emoji = []
        button_metadata = {}
        index = 0
        for row_data in button_data:
            for button_data in row_data:
                if index < len(REACTION_EMOJI):
                    emoji = REACTION_EMOJI[index]
                    button_descriptions.append("{} - {}".format(emoji, button_data['text']))
                    button_emoji.append(emoji)
                    button_metadata[emoji] ='{}#{}'.format(
                        prefix_key,
                        button_data['data'],
                    )
        return '\n'.join(button_descriptions), button_emoji, json.dumps(button_metadata)

    def send_message(self, message, key=None, update_message_id=None, recipient_id=None):
        if recipient_id is None:
            recipient_id = self.config['owner_id']
        
        room_id = recipient_id
        thread_id = None
        if ';' in recipient_id:
            parts = recipient_id.split(';', 1)
            room_id = parts[0]
            thread_id = parts[1]

        if isinstance(message, dict):
            buttons = None
            if 'buttons' in message:
                if not key:
                    raise ValueError("Using inline buttons requires you to pass a key")
                buttonlist, emoji, metadata = self.assemble_inline_buttons(message['buttons'], key)
            if 'photo' in message:
                self.bot.api.rooms_upload(room_id,
                                    message['photo'],
                                    msg=message.get('message'),
                                    tmid=thread_id,
                )
            else:
                if update_message_id is not None:
                    self.bot.api.chat_update(recipient_id, update_message_id, message['message'], tmd=thread)
                else:
                    self.bot.realtime.send_message(
                                          message['message'],
                                          room_id,
                                          thread_id=thread_id,
                    )
        else:
            if update_message_id is not None:
                self.bot.edit_message_text(
                    text=message,
                    chat_id=room_id,
                    message_id=update_message_id,
                    tmid=thread_id,
                )
            else:
                self.bot.realtime.send_message(message, room_id, thread_id=thread_id)

    def handle_message(self, bot, message):
        text = message.data.get("msg")
        direct = message.is_direct()
        if not direct:
            if not (text and text.startsWith('$')):
                return
            text = text[1:].strip()
        permission = self.get_permissions(None)

        message_id = message.data.get("_id")
        actor_id = message.data.get("u", {}).get("_id")
        room_id = message.data.get("rid")
        thread_id = message.data.get("tmid")
        combo_room_id = room_id
        if thread_id:
            combo_room_id = ';'.join([room_id, thread_id])
        elif not direct:
            combo_room_id = ';'.join([room_id, message_id])

        if self.config['debug']:
            logger.info("Received message from {}".format(actor_id))
        
        if permission not in PERMISSIONS:
            message.reply_in_thread("You're not my master. I won't talk to you!")
            return
        for handler in self.handlers:
            key = handler.key
            if text is not None:
                if handler.matches_message(update.message.text):
                    reply = handler.handle(
                        update.message.text,
                        db=self.db,
                        message_id=message_id,
                        actor_id=actor_id,
                        conversation_id=combo_room_id,
                        permission=permission,
                    )
                    self.send_message(reply, handler.key, recipient_id=combo_room_id)

        if direct:
            message.reply(get_generic_response())
        else:
            message.reply_in_thread(get_generic_response())

    def handle_inline_button(self, bot, message):
        reactions = message.data.get("reactions", {})
        import pprint
        pprint.pprint(reactions)


        permission = self.get_permissions(None)
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
                        if 'buttons' in answer:
                            buttonlist, emoji, metadata = self.assemble_inline_buttons(answer['buttons'], key)
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
    def handle_help(self, bot, message):
        """Send a message when the command /help is issued."""
        helptext = "I am HappyTetrahedron's personal butler.\n\b" \
                   "If you are not HappyTetrahedron, I fear I won't be useful to you."

        permission = self.get_permissions(None)

        if permission not in PERMISSIONS:
            update.message.reply_text(helptext, parse_mode="Markdown")
            return

        helptext = "I am your helpful assistant. I can perform a number of tasks.\n\n"
        for handler in self.handlers:
            handler_help = handler.help(permission)
            if handler_help:
                helptext += "*{}:*\n".format(handler.name)
                helptext += "{}\n".format(handler_help['summary'])
                for example in handler_help['examples']:
                    helptext += " _{}_\n".format(example)
                helptext += "\n"

        self.bot.api.chat_post_message(helptext,message.data.get("rid"), tmid=message.data.get("tmid", message.data.get("_id")))

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
        if 'bot_token' in config:
            bot = RocketchatBot(api_token=config['bot_token'], user_id=config['bot_id'], server_url=config['server_url'])
        else:
            bot = RocketchatBot(username=config['bot_user'], password=config['bot_password'], server_url=config['server_url'])
        self.bot = bot

        """Set up handlers"""
        for handler_class in HANDLER_CLASSES:
            handler = handler_class(self.config, self)
            self.handlers.append(handler)

        t = threading.Thread(target=self.scheduler_run)
        t.start()

        bot.add_handler(CommandHandler("help", self.handle_help))

        bot.add_handler(ReactionHandler(self.handle_inline_button))

        bot.add_handler(MessageHandler(self.handle_message))

        # Start the Bot
        asyncio.run(self._run_bot(bot))

        for handler in self.handlers:
            handler.teardown()

        self.exit.set()

    async def _run_bot(self, bot):
        await bot.run_forever()

    def scheduler_run(self):
        while not self.exit.is_set():
            for handler in self.handlers:
                try:
                    handler.run_periodically(self.periodic_db)
                except Exception as e:
                    logger.error("Exception on scheduler thread with handler {}".format(handler.key))
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
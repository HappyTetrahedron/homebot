from base_handler import *
import datetime
import logging
import random
from utils import PERM_ADMIN
from utils import get_exclamation
from utils import get_affirmation
from utils import escape_for_markdown
from calendar_service import CalendarService

logger = logging.getLogger(__name__)

time_format = "%H:%M"

class CalendarHandler(BaseHandler):

    calendar_service: CalendarService

    def __init__(self, config, messenger, service_hub):
        super().__init__(config, messenger, service_hub, key="calendars", name="Calendar Integration")
        self.calendar_service = service_hub.calendar
        if 'calendars' in config:
            self.config = config['calendars']
            self.enabled = True
        else:
            self.enabled = False


    def matches_message(self, message):
        m = message.lower()
        if m.startswith('toggle calendar report'):
            return True
        if m.startswith('events'):
            return True
        return False


    def help(self, permission):
        if not self.enabled:
            return
        if permission >= PERM_ADMIN:
            return {
                'summary': "Sends you a heads-up for upcoming calendar events.",
                'examples': [
                    "events",
                    "toggle calendar report",
                ],
            }
    

    def handle(self, message, **kwargs):
        m = message.lower()
        if m.startswith('toggle calendar report'):
            return self.toggle_report(kwargs['actor_id'], kwargs['db'])
        if m.startswith('events'):
            now = datetime.datetime.now()
            tomorrow = now + datetime.timedelta(days=1)
            end_time = datetime.datetime(
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                hour=23,
                minute=59,
            )
            return self.get_events_text(kwargs['actor_id'], now, end_time)
        return 'Something went wrong'


    def get_events_text(self, actor_id, from_time, to_time):
        events = self.calendar_service.get_events(actor_id, from_time, to_time)
        if not events:
            return f"{get_affirmation()}! There are no scheduled events."
        message = "\n\n".join(
            [
                "*{}:*\n{}".format(
                    calendar,
                    '\n'.join([self.format_event(e) for e in events[calendar]])
                )
                for calendar in events.keys()
            ]
        )
        return {
            'message': message,
            'parse_mode': 'markdownv2',
        }
    
    def format_event(self, event):
        return "{} \\- {}".format(event.get("start").strftime(time_format), escape_for_markdown(event.get("summary")))
                

    def toggle_report(self, actor, db):
        table = db['calendars']
        entry = table.find_one(actor=actor)
        if not entry:
            entry = {
                'actor': actor,
                'enabled': True,
                'next_message': self.get_next_reminder_date(),
            }
            table.insert(entry)
        else:
            entry['enabled'] = not entry['enabled']
            entry['next_message'] = self.get_next_reminder_date()
            print(entry)
            table.update(entry, ['actor'])

        if entry['enabled']:
            return "You will receive daily calendar reports."
        return "You will no longer receive calendar reports."

    def get_next_reminder_date(self):
        now = datetime.datetime.now()
        evening = datetime.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=19,
            minute=55,
        )

        if evening > now:
            return evening
        return evening + datetime.timedelta(days=1)


    def run_periodically(self, db):
        debug = self._debug
        table = db['calendars']
        send = self._messenger.send_message_from_thread
        if debug:
            logger.info("Querying calendars...")

        now = datetime.datetime.now()
        reminders = db.query('SELECT * FROM calendars WHERE enabled IS TRUE AND next_message < :now', now=now)

        tomorrow = now + datetime.timedelta(days=1)
        start_time = datetime.datetime(
            year=tomorrow.year,
            month=tomorrow.month,
            day=tomorrow.day,
            hour=0,
            minute=0,
        )
        end_time = datetime.datetime(
            year=tomorrow.year,
            month=tomorrow.month,
            day=tomorrow.day,
            hour=23,
            minute=59,
        )

        count = 0
        for reminder in reminders:
            count += 1
            if debug:
                logger.info("Sending calendar report {}".format(count))
            # this is so stupid I can't even
            # dataset returns dates as string but only accepts them as datetime
            reminder['next_message'] = datetime.datetime.strptime(reminder['next_message'], '%Y-%m-%d %H:%M:%S.%f')

            msg = self.get_events_text(reminder['actor'], start_time, end_time)

            if isinstance(msg, dict):
                # only send if there are actual tasks, which is conveniently only the case if msg is a dict
                msg['message'] = "Here's what's going on tomorrow:\n\n" + msg['message']
                send(msg, key=self.key, recipient_id=reminder['actor'] if 'actor' in reminder else None)

            reminder['next_message'] = self.get_next_reminder_date()

            if debug:
                logger.info("Updating report {}".format(count))
            table.update(reminder, ['actor'])
            if debug:
                logger.info("Finished report {}".format(count))
        if debug:
            logger.info("Sent out {} reports".format(count))

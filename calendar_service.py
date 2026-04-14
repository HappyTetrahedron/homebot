import datetime

from dateutil import parser
import requests
import caldav
import logging

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self, config):
        if 'calendars' in config:
            self.config = config['calendars']
            self.enabled = True
        else:
            self.enabled = False

    def can_see_events(self, telegram_user_id):
        return self.get_user_calendars(telegram_user_id) is not None
    
    def get_user_calendars(self, telegram_user_id):
        if not self.enabled:
            return None
        if not telegram_user_id in self.config.keys():
            return None
        return self.config[telegram_user_id]

    def get_events(self, telegram_user_id, start_date, end_date):
        real_start = start_date.astimezone()
        real_end = end_date.astimezone()
        calendars = self.get_user_calendars(telegram_user_id)

        result = {}

        for calendar in calendars:
            events = self._get_events_from_calendar(calendar, real_start, real_end)
            if not events:
                continue
            result[calendar.get("display_name", calendar.get("name"))] = events

        return result

    def _get_events_from_calendar(self, calendar, start_date, end_date):
        with caldav.DAVClient(
            url=calendar.get("url"),
            username=calendar.get("username"),
            password=calendar.get("password"),
        ) as client:
            p = client.principal()
            davcalendars = p.calendars()
            davcalendar = None
            if len(davcalendars) == 1:
                davcalendar = davcalendars[0]
            else:
                try:
                    davcalendar = next(iter([c for c in davcalendars if c.name == calendar.get("name")]))
                except StopIteration:
                    logger.warn("Could not match calendar name '{}'".format(calendar.get("name")))
                    logger.info("Found calendar names: {}".format(','.join([ c.name for c in davcalendars ])))
                    return []

            results = davcalendar.search(
                start=start_date,
                end=end_date,
                event=True,
                expand=True,
            )
            events = []
            for event in results:
                for component in event.icalendar_instance.walk():
                    if component.name != "VEVENT":
                        continue
                    if self._check_range(component, start_date, end_date):
                        events.append(self._convert_vevent_component(component, davcalendar))
            return events

    def _check_range(self, component, start_date, end_date):
        start = component.start
        end = component.end
        if isinstance(start, datetime.date):
            start = datetime.datetime.combine(start, datetime.datetime.min.time()).astimezone()
        if isinstance(end, datetime.date):
            end = datetime.datetime.combine(end, datetime.datetime.max.time()).astimezone()
        if not end:
            return start >= start_date and start <= end_date
        return start <= end_date and end >= start_date

    def _convert_vevent_component(self, component, calendar) -> dict[str, str]:
        ## quite some data is tossed away here - like, the recurring rule.
        cur = {}
        cur["calendar"] = f"{calendar}"
        cur["summary"] = component.get("summary")
        cur["description"] = component.get("description")
        cur["start"] = component.start
        endDate = component.end
        if endDate:
            cur["end"] = endDate
        ## For me the following line breaks because some imported calendar events
        ## came without dtstamp.  But dtstamp is mandatory according to the RFC
        cur["datestamp"] = component.get("dtstamp").dt
        return cur

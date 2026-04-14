from buttonhub_service import ButtonhubService
from moat_service import MoatService
from wekan_service import WekanService
from calendar_service import CalendarService


class ServiceHub:
    def __init__(self, config):
        self.wekan = WekanService(config)
        self.buttonhub = ButtonhubService(config)
        self.moat = MoatService(config)
        self.calendar = CalendarService(config)

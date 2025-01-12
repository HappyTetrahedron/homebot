from buttonhub_service import ButtonhubService
from moat_service import MoatService
from wekan_service import WekanService


class ServiceHub:
    def __init__(self, config):
        self.wekan = WekanService(config)
        self.buttonhub = ButtonhubService(config)
        self.moat = MoatService(config)

from wekan_service import WekanService


class ServiceHub:
    def __init__(self, config):
        self.wekan = WekanService(config)

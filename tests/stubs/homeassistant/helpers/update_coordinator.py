class UpdateFailed(Exception):
    pass

class DataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        pass

class CoordinatorEntity:
    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator

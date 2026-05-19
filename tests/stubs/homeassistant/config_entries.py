class ConfigEntryNotReady(Exception):
    pass


class ConfigEntry:
    pass


class ConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)

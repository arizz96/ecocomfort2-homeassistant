class FanEntityFeature:
    SET_SPEED = 1
    PRESET_MODE = 2
    TURN_ON = 4
    TURN_OFF = 8

class FanEntity:
    _attr_preset_modes = None
    _attr_unique_id = None
    _attr_device_info = None
    _attr_has_entity_name = False

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def speed_count(self):
        return 4

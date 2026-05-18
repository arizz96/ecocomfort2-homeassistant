from enum import Enum

class HVACMode(str, Enum):
    OFF = "off"
    FAN_ONLY = "fan_only"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"

class ClimateEntityFeature:
    TARGET_TEMPERATURE = 1
    TURN_OFF = 2
    TURN_ON = 4

class ClimateEntity:
    pass

"""Constants for the Ecocomfort 2.0 VMC integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ecocomfort2"

MANUFACTURER = "Intelliclima"
MODEL = "Ecocomfort 2.0"

# BLE local name prefix the VMC advertises with (e.g. "Comfort_1A2B").
DEVICE_NAME_PREFIX = "Comfort"

# How often the device is polled for fresh readings.
UPDATE_INTERVAL = timedelta(seconds=30)

# Re-sync the device clock at most this often.
CLOCK_SYNC_INTERVAL = timedelta(hours=1)

# ------------------------------------------------------------------------------
# BLE GATT service + characteristics
# ------------------------------------------------------------------------------
SERVICE_UUID = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"

# Read: firmware version, serial
CHAR_INFO = "f5f56229-dd4f-480f-a829-9189269d8b37"
# Read: real-time temperature, humidity, VOC, direction
CHAR_STATE = "438d3433-7e5a-459a-a8e4-66343fad2bb0"
# R/W: operating mode (2 bytes: preset + speed)
CHAR_OPER = "b9d6f678-bc0d-4a73-90c8-60b0f07301f1"
# R/W: device configuration (12 bytes)
CHAR_CONFIG = "d3dac48e-b4e1-4f3a-8715-326ddf1da89a"
# Write: clock sync (8 bytes)
CHAR_CLOCK = "82788997-49e4-4533-b949-7ed433678044"
# R/W: sensor calibration offsets (4 bytes)
CHAR_ADVANCED = "f8b2284e-61dd-44e3-a782-a93c9503ab2d"
# Standard GAP Device Name (e.g. "ECMF2-0000abcd"), used to label log lines.
# Readable through ESPHome proxies; BlueZ hides the GAP service from clients.
CHAR_DEVICE_NAME = "00002a00-0000-1000-8000-00805f9b34fb"

# ------------------------------------------------------------------------------
# Operating mode protocol (C_SETTING_OPERATION, 2 bytes)
# ------------------------------------------------------------------------------
# Byte 0 - preset / direction
MODE_OFF = 0x00
MODE_IN = 0x01
MODE_OUT = 0x02
MODE_IN_OUT = 0x03
MODE_SENSOR_AUTO = 0x04

# Speed byte (byte 1) flags
SPEED_AUTO_FLAG = 0x10  # device controls the speed autonomously ("Auto" preset)
SPEED_ADVANCED_FLAG = 0x20  # read-only: an advanced threshold bumped the speed one step
SPEED_BOOST_FLAG = 0x40  # read-only: device auto-triggered boost
SPEED_SLEEP_FLAG = 0x80  # read-only: Sleep mode (minimum speed, below Vel 1)

PRESET_IN = "In"
PRESET_OUT = "Out"
PRESET_IN_OUT = "In/Out"
PRESET_SENSOR = "Sensor"
PRESET_AUTO = "Auto"

PRESET_MODES = [PRESET_IN, PRESET_OUT, PRESET_IN_OUT, PRESET_SENSOR, PRESET_AUTO]

PRESET_TO_MODE = {
    PRESET_IN: MODE_IN,
    PRESET_OUT: MODE_OUT,
    PRESET_IN_OUT: MODE_IN_OUT,
    PRESET_SENSOR: MODE_SENSOR_AUTO,
    PRESET_AUTO: MODE_SENSOR_AUTO,
}

# Device speed levels map to four ordered HA speeds (25/50/75/100%).
#   1 = Sleep, 2 = Vel1, 3 = Vel2, 4 = Vel3
SPEED_RANGE = (1, 4)
DEFAULT_SPEED = 0x03  # Vel2

# ------------------------------------------------------------------------------
# Configuration protocol (C_CONFIGURATION, 12 bytes)
# ------------------------------------------------------------------------------
# When writing, 0x7F in a byte means "preserve existing value".
CONFIG_PRESERVE = 0x7F

SEASON_WINTER = "Winter"
SEASON_SUMMER = "Summer"
SEASON_OPTIONS = [SEASON_WINTER, SEASON_SUMMER]
# Byte 4 write values that preserve free cooling while changing season.
SEASON_WRITE_SUMMER = 0x1F
SEASON_WRITE_WINTER = 0x00

FREE_COOLING_OFF = "Off"
FREE_COOLING_LOW = "Low"
FREE_COOLING_MEDIUM = "Medium"
FREE_COOLING_HIGH = "High"
FREE_COOLING_OPTIONS = [
    FREE_COOLING_OFF,
    FREE_COOLING_LOW,
    FREE_COOLING_MEDIUM,
    FREE_COOLING_HIGH,
]
FREE_COOLING_TO_VALUE = {
    FREE_COOLING_OFF: 0,
    FREE_COOLING_LOW: 1,
    FREE_COOLING_MEDIUM: 2,
    FREE_COOLING_HIGH: 3,
}
VALUE_TO_FREE_COOLING = {value: name for name, value in FREE_COOLING_TO_VALUE.items()}
# Byte 4 prefix that tells the device "free cooling write, preserve season".
FREE_COOLING_WRITE_PREFIX = 0x70

# The "advanced" flag is encoded as +128 on the humidity / VOC threshold byte.
THRESHOLD_ADVANCED_FLAG = 128

# ------------------------------------------------------------------------------
# Enum states for coded values. Keys are translated in strings.json.
# ------------------------------------------------------------------------------
# C_CONFIGURATION byte 0. "Main"/"satellite" is the Intelliclima app's own
# wording (1 = main, 2 = satellite per the vendor cloud API; 0 = not part of a
# group per the original ESPHome package).
VALUE_TO_ROLE = {0: "standalone", 1: "main", 2: "satellite"}
ROLE_OPTIONS = list(VALUE_TO_ROLE.values())

# C_STATE byte 2: the airflow direction the unit is running right now (it
# alternates in In/Out mode). Assumed to follow the device's own direction
# encoding used by the mode byte (1 = in, 2 = out); no source documents it.
VALUE_TO_DIRECTION = {1: "intake", 2: "exhaust"}
# Shown while the unit is off, when there's no airflow to report.
DIRECTION_OFF = "off"
DIRECTION_OPTIONS = [DIRECTION_OFF, *VALUE_TO_DIRECTION.values()]

# Running mode, decoded from C_STATE byte 0 (low nibble) plus the
# sensor/program flag in byte 1.
OPERATING_MODE_OPTIONS = ["off", "in", "out", "in_out", "sensor", "auto"]

# Running speed, decoded from C_STATE byte 1 (low 3 bits after flag overrides).
RUNNING_SPEED_MASK = 0x07
SPEED_LEVEL_OPTIONS = ["off", "sleep", "speed_1", "speed_2", "speed_3", "boost"]
VALUE_TO_SPEED_LEVEL = {1: "sleep", 2: "speed_1", 3: "speed_2", 4: "speed_3", 5: "boost"}

# Sensor-mode threshold levels (C_CONFIGURATION bytes 1-3, low bits).
THRESHOLD_OPTIONS = ["off", "low", "medium", "high"]

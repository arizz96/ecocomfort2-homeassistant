"""Shared fixtures for Ecocomfort 2 tests."""
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "stubs"))

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState  # noqa: E402


MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"


def make_info_bytes(major=1, minor=2, patch=3, serial_hex="AABBCCDDEE00"):
    """Build a C_INFO payload with nibble-encoded firmware."""
    # Byte 0: high nibble = major, low nibble = upper 4 bits of combined
    # combined (12 bits) = minor (6) | patch (6)
    combined = ((minor & 0x3F) << 6) | (patch & 0x3F)
    byte0 = ((major & 0x0F) << 4) | ((combined >> 8) & 0x0F)
    byte1 = combined & 0xFF
    header = bytes([byte0, byte1])
    serial = bytes.fromhex(serial_hex)
    return header + serial


def make_state_bytes(direction=2, temp_c=21.5, humidity_pct=55.0, voc=100):
    """Build a C_STATE payload (9 bytes: 2 reserved + 1 direction + 2 temp + 2 hum + 2 voc)."""
    temp_raw = int(temp_c * 100)
    hum_raw = int(humidity_pct * 100)
    return struct.pack("<xxBhHH", direction, temp_raw, hum_raw, voc)


def make_oper_bytes(mode=1, speed=2, boost=False, auto=False, night=False):
    """Build a C_SETTING_OPER payload."""
    flags = (speed & 0x0F)
    if auto:
        flags |= 0x10
    if boost:
        flags |= 0x40
    if night:
        flags |= 0x80
    return bytes([mode, flags])


def make_config_bytes(
    role=0,
    humidity_threshold=1,
    humidity_advanced=False,
    luminosity_threshold=1,
    voc_threshold=1,
    voc_advanced=False,
    free_cooling=0,
    season=0,
):
    """Build a C_CONFIGURATION payload (12 bytes)."""
    hum_byte = (humidity_threshold & 0x7F) | (0x80 if humidity_advanced else 0)
    voc_byte = (voc_threshold & 0x7F) | (0x80 if voc_advanced else 0)
    byte4 = (free_cooling & 0x03) | (0x08 if season else 0)
    return bytes([role, hum_byte, luminosity_threshold, voc_byte, byte4, 0x00,
                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def make_advanced_bytes(temp_offset=0.0, hum_offset=0.0):
    """Build a C_ADVANCED payload (big-endian int16 × 100)."""
    return struct.pack(">hh", int(temp_offset * 100), int(hum_offset * 100))


@pytest.fixture
def device():
    """Return a fresh EcocomfortDevice with a mocked BleakClient."""
    dev = EcocomfortDevice(MAC_ADDRESS)
    mock_client = AsyncMock()
    mock_client.is_connected = True
    dev.client = mock_client
    dev.state.connected = True
    return dev

"""Shared fixtures for Ecocomfort 2 tests."""
import struct
import sys
import os

# Inject lightweight HA stubs before any component import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "stubs"))

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState  # noqa: E402


MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"


def make_info_bytes(fw_major=1, fw_minor=2, fw_patch=3, serial_hex="DEADBEEF"):
    """Build a valid C_INFO payload."""
    fw = bytes([fw_major, fw_minor, fw_patch, 0])
    serial = bytes.fromhex(serial_hex)
    return fw + serial


def make_state_bytes(temp_c=21.5, humidity=55, voc=100, direction=2):
    """Build a valid C_STATE payload."""
    temp_raw = int(temp_c * 10)
    return struct.pack("<hBHBxx", temp_raw, humidity, voc, direction)


def make_oper_bytes(mode=1):
    """Build a valid C_SETTING_OPER payload."""
    return struct.pack("<H", mode)


@pytest.fixture
def device():
    """Return a fresh EcocomfortDevice with a mocked BleakClient."""
    dev = EcocomfortDevice(MAC_ADDRESS)
    mock_client = AsyncMock()
    mock_client.is_connected = True
    dev.client = mock_client
    return dev

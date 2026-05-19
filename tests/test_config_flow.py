"""Tests for Ecocomfort 2 config flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ecocomfort2.config_flow import EcocomfortConfigFlow
from tests.conftest import MAC_ADDRESS


def make_flow():
    """Return a config flow instance with mocked HA plumbing."""
    flow = EcocomfortConfigFlow()
    flow.hass = MagicMock()
    flow._async_set_unique_id_already_configured = MagicMock(return_value=False)
    # async_set_unique_id and _abort_if_unique_id_configured are called as regular methods
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    return flow


class TestAsyncStepUser:
    async def test_no_input_no_devices_shows_form(self):
        flow = make_flow()
        with patch.object(flow, "_discover_devices", AsyncMock(return_value=[])):
            result = await flow.async_step_user(user_input=None)
        flow.async_show_form.assert_called_once()
        assert flow.async_show_form.call_args[1]["step_id"] == "user"

    async def test_no_input_with_devices_shows_discovery_form(self):
        flow = make_flow()
        with patch.object(flow, "_discover_devices", AsyncMock(return_value=[MAC_ADDRESS])):
            result = await flow.async_step_user(user_input=None)
        # Should render the select_device form
        flow.async_show_form.assert_called_once()
        assert flow.async_show_form.call_args[1]["step_id"] == "select_device"

    async def test_with_input_creates_entry(self):
        flow = make_flow()
        result = await flow.async_step_user(user_input={"mac": MAC_ADDRESS, "name": "My Device"})
        flow.async_create_entry.assert_called_once()
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"]["mac"] == MAC_ADDRESS

    async def test_mac_is_uppercased(self):
        flow = make_flow()
        lower_mac = MAC_ADDRESS.lower()
        await flow.async_step_user(user_input={"mac": lower_mac})
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"]["mac"] == MAC_ADDRESS

    async def test_default_name_used_when_omitted(self):
        flow = make_flow()
        await flow.async_step_user(user_input={"mac": MAC_ADDRESS})
        call_kwargs = flow.async_create_entry.call_args[1]
        assert MAC_ADDRESS in call_kwargs["title"]

    async def test_unique_id_set_from_mac(self):
        flow = make_flow()
        await flow.async_step_user(user_input={"mac": MAC_ADDRESS})
        flow.async_set_unique_id.assert_awaited_once_with(MAC_ADDRESS)

    async def test_abort_if_already_configured(self):
        flow = make_flow()
        await flow.async_step_user(user_input={"mac": MAC_ADDRESS})
        flow._abort_if_unique_id_configured.assert_called_once()


class TestAsyncStepSelectDevice:
    async def test_creates_entry_from_selected_device(self):
        flow = make_flow()
        result = await flow.async_step_select_device(
            {"device": MAC_ADDRESS, "name": "Test Unit"}
        )
        flow.async_create_entry.assert_called_once()
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"]["mac"] == MAC_ADDRESS

    async def test_mac_is_uppercased(self):
        flow = make_flow()
        await flow.async_step_select_device({"device": MAC_ADDRESS.lower()})
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"]["mac"] == MAC_ADDRESS

    async def test_sets_unique_id(self):
        flow = make_flow()
        await flow.async_step_select_device({"device": MAC_ADDRESS})
        flow.async_set_unique_id.assert_awaited_once_with(MAC_ADDRESS)


SERVICE_UUID = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"


def make_adv_results(*entries):
    """Build return value for BleakScanner.discover(return_adv=True).

    Each entry is (address, device_name, service_uuids).
    Returns dict[address, (BLEDevice, AdvertisementData)].
    """
    results = {}
    for address, name, uuids in entries:
        device = MagicMock()
        device.name = name
        device.address = address
        adv = MagicMock()
        adv.service_uuids = uuids
        results[address] = (device, adv)
    return results


class TestDiscoverDevices:
    async def test_discovers_by_name(self):
        flow = make_flow()
        adv_data = make_adv_results((MAC_ADDRESS, "Ecocomfort2-ABC", []))
        with patch("custom_components.ecocomfort2.config_flow.BleakScanner") as mock_cls:
            mock_cls.discover = AsyncMock(return_value=adv_data)
            result = await flow._discover_devices()
        assert MAC_ADDRESS in result

    async def test_discovers_by_service_uuid(self):
        flow = make_flow()
        adv_data = make_adv_results((MAC_ADDRESS, "Unknown", [SERVICE_UUID]))
        with patch("custom_components.ecocomfort2.config_flow.BleakScanner") as mock_cls:
            mock_cls.discover = AsyncMock(return_value=adv_data)
            result = await flow._discover_devices()
        assert MAC_ADDRESS in result

    async def test_ignores_unrelated_device(self):
        flow = make_flow()
        adv_data = make_adv_results(("11:22:33:44:55:66", "SomeOtherDevice", []))
        with patch("custom_components.ecocomfort2.config_flow.BleakScanner") as mock_cls:
            mock_cls.discover = AsyncMock(return_value=adv_data)
            result = await flow._discover_devices()
        assert result == []

    async def test_returns_empty_list_on_exception(self):
        flow = make_flow()
        with patch("custom_components.ecocomfort2.config_flow.BleakScanner") as mock_cls:
            mock_cls.discover = AsyncMock(side_effect=OSError("bluetooth unavailable"))
            result = await flow._discover_devices()
        assert result == []

    async def test_no_duplicate_entries(self):
        """Device matched by both name and UUID should appear exactly once."""
        flow = make_flow()
        # Device name matches AND its UUID matches — dict keying by address deduplicates
        adv_data = make_adv_results((MAC_ADDRESS, "Ecocomfort2-X", [SERVICE_UUID]))
        with patch("custom_components.ecocomfort2.config_flow.BleakScanner") as mock_cls:
            mock_cls.discover = AsyncMock(return_value=adv_data)
            result = await flow._discover_devices()
        assert result.count(MAC_ADDRESS) == 1

    async def test_fallback_to_name_only_on_type_error(self):
        """TypeError from return_adv triggers fallback to name-only scan."""
        flow = make_flow()

        def discover_side_effect(**kwargs):
            if kwargs.get("return_adv"):
                raise TypeError("return_adv not supported")
            device = MagicMock()
            device.name = "Ecocomfort2-Old"
            device.address = MAC_ADDRESS
            return [device]

        with patch("custom_components.ecocomfort2.config_flow.BleakScanner") as mock_cls:
            mock_cls.discover = AsyncMock(side_effect=discover_side_effect)
            result = await flow._discover_devices()
        assert MAC_ADDRESS in result

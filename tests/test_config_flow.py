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


class TestDiscoverDevices:
    async def test_discovers_by_name(self):
        flow = make_flow()

        mock_device = MagicMock()
        mock_device.name = "Ecocomfort2-ABC"
        mock_device.address = MAC_ADDRESS
        mock_device.metadata = {}

        mock_scanner = AsyncMock()
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        with patch("custom_components.ecocomfort2.config_flow.BleakScanner", return_value=mock_scanner):
            result = await flow._discover_devices()

        assert MAC_ADDRESS in result

    async def test_discovers_by_service_uuid(self):
        flow = make_flow()
        service_uuid = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"

        mock_device = MagicMock()
        mock_device.name = "Unknown"
        mock_device.address = MAC_ADDRESS
        mock_device.metadata = {"uuids": [service_uuid]}

        mock_scanner = AsyncMock()
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        with patch("custom_components.ecocomfort2.config_flow.BleakScanner", return_value=mock_scanner):
            result = await flow._discover_devices()

        assert MAC_ADDRESS in result

    async def test_ignores_unrelated_device(self):
        flow = make_flow()

        mock_device = MagicMock()
        mock_device.name = "SomeOtherDevice"
        mock_device.address = "11:22:33:44:55:66"
        mock_device.metadata = {}

        mock_scanner = AsyncMock()
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        with patch("custom_components.ecocomfort2.config_flow.BleakScanner", return_value=mock_scanner):
            result = await flow._discover_devices()

        assert result == []

    async def test_returns_empty_list_on_exception(self):
        flow = make_flow()

        mock_scanner = AsyncMock()
        mock_scanner.discover.side_effect = OSError("bluetooth unavailable")

        with patch("custom_components.ecocomfort2.config_flow.BleakScanner", return_value=mock_scanner):
            result = await flow._discover_devices()

        assert result == []

    async def test_no_duplicate_entries(self):
        """Same device matched by both name and UUID should appear once."""
        flow = make_flow()
        service_uuid = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"

        mock_device = MagicMock()
        mock_device.name = "Ecocomfort2-X"
        mock_device.address = MAC_ADDRESS
        mock_device.metadata = {"uuids": [service_uuid]}

        mock_scanner = AsyncMock()
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        with patch("custom_components.ecocomfort2.config_flow.BleakScanner", return_value=mock_scanner):
            result = await flow._discover_devices()

        assert result.count(MAC_ADDRESS) == 1

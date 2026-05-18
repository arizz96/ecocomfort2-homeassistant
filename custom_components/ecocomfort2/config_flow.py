"""Config flow for Ecocomfort 2 integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from bleak import BleakScanner
from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecocomfort2"


class EcocomfortConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ecocomfort 2."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            mac_address = user_input[CONF_MAC].upper()

            # Check if device is already configured
            await self.async_set_unique_id(mac_address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, f"Ecocomfort 2 {mac_address}"),
                data={CONF_MAC: mac_address},
            )

        # Try to auto-discover Ecocomfort 2 devices
        discovered_devices = await self._discover_devices()

        if discovered_devices:
            return await self.async_step_discovery(discovered_devices)

        schema = vol.Schema(
            {
                vol.Required(CONF_MAC): str,
                vol.Optional(CONF_NAME, default="Ecocomfort 2"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "devices": "\n".join(discovered_devices)
                if discovered_devices
                else "No devices found"
            },
        )

    async def async_step_discovery(
        self, discovered_devices: list
    ) -> FlowResult:
        """Handle device discovery."""
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In(
                        {dev: dev for dev in discovered_devices}
                    ),
                    vol.Optional(CONF_NAME, default="Ecocomfort 2"): str,
                }
            ),
            description_placeholders={"devices": len(discovered_devices)},
        )

    async def async_step_select_device(
        self, user_input: Dict[str, Any]
    ) -> FlowResult:
        """Handle device selection from discovery."""
        mac_address = user_input["device"].upper()

        await self.async_set_unique_id(mac_address)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=user_input.get(CONF_NAME, f"Ecocomfort 2 {mac_address}"),
            data={CONF_MAC: mac_address},
        )

    async def _discover_devices(self) -> list:
        """Discover Ecocomfort 2 devices via BLE."""
        try:
            scanner = BleakScanner()
            devices = await scanner.discover()

            ecocomfort_devices = []
            for device in devices:
                # Look for Ecocomfort 2 devices by name or service UUID
                if device.name and "ecocomfort" in device.name.lower():
                    ecocomfort_devices.append(device.address)
                elif device.metadata.get("uuids"):
                    service_uuid = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"
                    if service_uuid in device.metadata.get("uuids", []):
                        ecocomfort_devices.append(device.address)

            return ecocomfort_devices
        except Exception as e:
            _LOGGER.error("Error discovering devices: %s", e)
            return []

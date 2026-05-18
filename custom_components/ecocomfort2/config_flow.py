"""Config flow for Ecocomfort 2 integration."""
import logging
from typing import Any

import voluptuous as vol
from bleak import BleakScanner
from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecocomfort2"


class EcocomfortConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ecocomfort 2."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac_address = user_input[CONF_MAC].upper()
            await self.async_set_unique_id(mac_address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, f"Ecocomfort 2 {mac_address}"),
                data={CONF_MAC: mac_address},
            )

        discovered_devices = await self._discover_devices()

        if discovered_devices:
            return await self.async_step_discovery(discovered_devices)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC): str,
                    vol.Optional(CONF_NAME, default="Ecocomfort 2"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "devices": "\n".join(discovered_devices) if discovered_devices else "No devices found"
            },
        )

    async def async_step_discovery(self, discovered_devices: list) -> dict[str, Any]:
        """Handle device discovery."""
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In({dev: dev for dev in discovered_devices}),
                    vol.Optional(CONF_NAME, default="Ecocomfort 2"): str,
                }
            ),
            description_placeholders={"devices": len(discovered_devices)},
        )

    async def async_step_select_device(self, user_input: dict[str, Any]) -> dict[str, Any]:
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
        service_uuid = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"
        found: dict[str, str] = {}
        try:
            # bleak 2.x: discover(return_adv=True) → dict[address, (BLEDevice, AdvertisementData)]
            results = await BleakScanner.discover(return_adv=True)
            for address, (device, adv) in results.items():
                if device.name and "ecocomfort" in device.name.lower():
                    found[address] = address
                elif service_uuid in adv.service_uuids:
                    found[address] = address
        except TypeError:
            # Fallback for bleak < 0.22 without return_adv
            for device in await BleakScanner.discover():
                if device.name and "ecocomfort" in device.name.lower():
                    found[device.address] = device.address
        except Exception as exc:
            _LOGGER.error("Error discovering devices: %s", exc)

        return list(found)

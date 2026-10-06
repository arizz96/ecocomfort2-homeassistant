"""Config flow for the Ecocomfort 2.0 VMC integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DEVICE_NAME_PREFIX, DOMAIN, SERVICE_UUID


def _advertises_service(info: BluetoothServiceInfoBleak) -> bool:
    """Return True if the advertisement carries the VMC's GATT service UUID."""
    return SERVICE_UUID.lower() in {uuid.lower() for uuid in info.service_uuids}


def _is_ecocomfort2(info: BluetoothServiceInfoBleak) -> bool:
    """Identify a VMC either by advertised name or by its service UUID.

    Many units don't broadcast a local name at all (the BLE stack then
    reports the MAC address as the "name"), so the service UUID is the
    more reliable signal; the name prefix is kept as a fallback for units
    that do advertise one.
    """
    if info.name and info.name.startswith(DEVICE_NAME_PREFIX):
        return True
    return _advertises_service(info)


def _title_for(info: BluetoothServiceInfoBleak) -> str:
    """Build a human-friendly title, falling back when no name is broadcast."""
    if info.name and info.name.upper() != info.address.upper():
        return info.name
    return f"Ecocomfort VMC {info.address}"


class EcoComfort2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ecocomfort 2.0 devices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise discovery state."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a device discovered via Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        title = _title_for(discovery_info)
        self.context["title_placeholders"] = {"name": title}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered device."""
        assert self._discovery_info is not None
        title = _title_for(self._discovery_info)
        if user_input is not None:
            return self.async_create_entry(
                title=title, data={CONF_ADDRESS: self._discovery_info.address}
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": title},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup by picking from discovered devices."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered.get(address, address),
                data={CONF_ADDRESS: address},
            )

        current_addresses = self._async_current_ids()
        for info in async_discovered_service_info(self.hass):
            if info.address in current_addresses or info.address in self._discovered:
                continue
            if _is_ecocomfort2(info):
                self._discovered[info.address] = _title_for(info)

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{name} ({address})"
                            for address, name in self._discovered.items()
                        }
                    )
                }
            ),
        )

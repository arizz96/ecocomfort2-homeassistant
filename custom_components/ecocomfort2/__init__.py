"""The Ecocomfort 2.0 VMC integration (direct BLE, no ESPHome proxy)."""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import EcoComfort2ConfigEntry, EcoComfort2Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _migrate_exhaust_readings(registry: er.EntityRegistry, address: str) -> None:
    """Turn the exhaust_* sensors back into temperature/humidity/voc.

    Same data (room air), so the entities are renamed in place, entity ID and
    unique ID, to keep their history. Any leftover entry of the pre-split
    entity is dropped first: it holds the unique ID and the entity ID.
    """
    for key in ("temperature", "humidity", "voc"):
        old_id = registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, f"{address}_exhaust_{key}"
        )
        if old_id is None:
            continue
        if leftover := registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, f"{address}_{key}"
        ):
            registry.async_remove(leftover)
        new_id = None
        if old_id.endswith(f"_exhaust_{key}"):
            new_id = f"{old_id.removesuffix(f'_exhaust_{key}')}_{key}"
            if registry.async_get(new_id) is not None:
                new_id = None
        registry.async_update_entity(
            old_id, new_unique_id=f"{address}_{key}", new_entity_id=new_id or old_id
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: EcoComfort2ConfigEntry
) -> bool:
    """Set up Ecocomfort 2.0 from a config entry."""
    address: str = entry.data[CONF_ADDRESS]

    if bluetooth.async_ble_device_from_address(hass, address.upper(), True) is None:
        raise ConfigEntryNotReady(
            f"Could not find Ecocomfort2 device with address {address}"
        )

    # Drop registry entries of entities that were replaced: the thresholds used
    # to be number entities (now selects with the same unique IDs), the Sleep
    # Mode (briefly Night Mode) and Boost Active binary sensors only restated
    # Actual Speed, the offset sensors restated the offset numbers, and the
    # firmware sensor restated the device page. The intake reading set is
    # gone; the exhaust one (room air) is renamed back to temperature/
    # humidity/VOC below.
    registry = er.async_get(hass)
    _migrate_exhaust_readings(registry, address)
    for platform, key in (
        (Platform.NUMBER, "humidity_threshold"),
        (Platform.NUMBER, "luminosity_threshold"),
        (Platform.NUMBER, "voc_threshold"),
        (Platform.BINARY_SENSOR, "night_active"),
        (Platform.BINARY_SENSOR, "sleep_active"),
        (Platform.BINARY_SENSOR, "boost_active"),
        (Platform.SENSOR, "temp_offset"),
        (Platform.SENSOR, "humidity_offset"),
        (Platform.SENSOR, "firmware"),
        (Platform.SENSOR, "intake_temperature"),
        (Platform.SENSOR, "intake_humidity"),
        (Platform.SENSOR, "intake_voc"),
    ):
        if entity_id := registry.async_get_entity_id(
            platform, DOMAIN, f"{address}_{key}"
        ):
            registry.async_remove(entity_id)

    coordinator = EcoComfort2Coordinator(hass, entry, address)
    # Don't wait for the first BLE session here: through a proxy it can take
    # tens of seconds (connect, service discovery, possibly pairing), and HA
    # waits for this setup during startup. Entities start out unavailable and
    # fill in when the first refresh completes in the background.
    coordinator.data = coordinator.device.state
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(
        hass, coordinator.async_first_refresh(), f"{DOMAIN} first refresh {address}"
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EcoComfort2ConfigEntry
) -> bool:
    """Unload a config entry.

    There's no link to close: polls and commands disconnect when they finish,
    and Home Assistant cancels a poll still running (a background task) after
    this returns, which disconnects too. Waiting for the device lock here made
    a reload wait for a hung poll, up to POLL_TIMEOUT.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

"""Climate platform for Ecocomfort 2."""
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_MAC, TEMP_CELSIUS, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)

# Operating modes mapping
HVAC_MODES = {
    0: HVACMode.OFF,
    1: HVACMode.FAN_ONLY,
    2: HVACMode.HEAT,
    3: HVACMode.COOL,
    4: HVACMode.AUTO,
}

HVAC_TO_MODE = {v: k for k, v in HVAC_MODES.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    device = data["device"]
    coordinator = data["coordinator"]

    async_add_entities(
        [EcocomfortClimate(coordinator, device, config_entry)],
        update_before_add=True,
    )


class EcocomfortClimate(CoordinatorEntity, ClimateEntity):
    """Climate entity for Ecocomfort 2 device."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = list(HVAC_MODES.values())

    def __init__(
        self,
        coordinator,
        device: EcocomfortDevice,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self.device = device
        self._attr_unique_id = f"{config_entry.data[CONF_MAC]}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.data[CONF_MAC])},
            "name": f"Ecocomfort 2 {config_entry.data[CONF_MAC]}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.device.state.temperature

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self.device.state.humidity

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        mode = self.device.state.operating_mode
        if mode is None:
            return HVACMode.OFF
        return HVAC_MODES.get(mode & 0xFF, HVACMode.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        if hvac_mode not in HVAC_TO_MODE:
            return

        mode_value = HVAC_TO_MODE[hvac_mode]
        success = await self.device.async_set_operating_mode(mode_value)

        if success:
            await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        return {
            "voc": self.device.state.voc,
            "direction": self.device.state.direction,
            "firmware": self.device.state.firmware,
            "serial": self.device.state.serial,
        }

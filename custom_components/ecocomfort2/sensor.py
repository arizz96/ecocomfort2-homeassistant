"""Sensor platform for Ecocomfort 2."""
import logging
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MAC,
    CONCENTRATION_PARTS_PER_BILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import EcocomfortDevice, MODE_TO_PRESET, SPEED_TO_PCT

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcocomfortSensorDescription(SensorEntityDescription):
    value_fn: callable = None


SENSOR_DESCRIPTIONS = [
    # Environmental (C_STATE)
    EcocomfortSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda state: state.temperature,
    ),
    EcocomfortSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda state: state.humidity,
    ),
    EcocomfortSensorDescription(
        key="voc",
        translation_key="voc",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_BILLION,
        value_fn=lambda state: state.voc,
    ),
    EcocomfortSensorDescription(
        key="direction",
        translation_key="direction",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.direction,
    ),
    # Operating state readback (C_SETTING_OPER)
    EcocomfortSensorDescription(
        key="actual_mode",
        translation_key="actual_mode",
        value_fn=lambda state: MODE_TO_PRESET.get(state.operating_mode, "Off")
        if state.operating_mode is not None
        else None,
    ),
    EcocomfortSensorDescription(
        key="actual_speed",
        translation_key="actual_speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: SPEED_TO_PCT.get(state.speed),
    ),
    # Device information (C_INFO)
    EcocomfortSensorDescription(
        key="firmware",
        translation_key="firmware",
        value_fn=lambda state: state.firmware,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            EcocomfortSensor(data["coordinator"], data["device"], config_entry, desc)
            for desc in SENSOR_DESCRIPTIONS
        ],
        update_before_add=True,
    )


class EcocomfortSensor(CoordinatorEntity, SensorEntity):
    entity_description: EcocomfortSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, device: EcocomfortDevice, config_entry, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.device = device
        mac = config_entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Ecocomfort 2 {mac}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.device.state)

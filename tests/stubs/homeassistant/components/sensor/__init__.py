from dataclasses import dataclass, field
from typing import Any, Callable, Optional

class SensorStateClass:
    MEASUREMENT = "measurement"

class SensorDeviceClass:
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"
    VOLATILE_ORGANIC_COMPOUNDS_PARTS = "volatile_organic_compounds_parts"

@dataclass
class SensorEntityDescription:
    key: str = ""
    translation_key: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    native_unit_of_measurement: Optional[str] = None

class SensorEntity:
    entity_description: Any = None
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_has_entity_name: bool = False

    @property
    def unique_id(self):
        return self._attr_unique_id

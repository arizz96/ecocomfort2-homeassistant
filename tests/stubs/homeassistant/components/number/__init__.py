from dataclasses import dataclass
from typing import Optional, Any

class NumberMode:
    SLIDER = "slider"
    BOX = "box"

@dataclass
class NumberEntityDescription:
    key: str = ""
    translation_key: Optional[str] = None
    native_unit_of_measurement: Optional[str] = None
    native_min_value: float = 0
    native_max_value: float = 100
    native_step: float = 1
    mode: str = NumberMode.SLIDER

class NumberEntity:
    entity_description: Any = None
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_has_entity_name: bool = False

    @property
    def unique_id(self):
        return self._attr_unique_id

from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class SwitchEntityDescription:
    key: str = ""
    translation_key: Optional[str] = None

class SwitchEntity:
    entity_description: Any = None
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_has_entity_name: bool = False

    @property
    def unique_id(self):
        return self._attr_unique_id

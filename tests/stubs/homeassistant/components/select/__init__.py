from dataclasses import dataclass, field
from typing import Optional, Any, List

@dataclass
class SelectEntityDescription:
    key: str = ""
    translation_key: Optional[str] = None
    options: Optional[List[str]] = None

class SelectEntity:
    entity_description: Any = None
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_has_entity_name: bool = False
    _attr_options: Optional[List[str]] = None

    @property
    def unique_id(self):
        return self._attr_unique_id

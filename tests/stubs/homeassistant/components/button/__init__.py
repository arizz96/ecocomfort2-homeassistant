from typing import Optional

class ButtonEntity:
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_has_entity_name: bool = False
    _attr_translation_key: Optional[str] = None

    @property
    def unique_id(self):
        return self._attr_unique_id

"""Tuya Cloud Custom - Robust Binary Sensor platform with translate support."""

import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom binary sensors."""
    devices = hass.data[DOMAIN]["devices"]
    sensors = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "binary_sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudBinarySensor(hass, device, dp))
    async_add_entities(sensors)
    _LOGGER.info("[%s] ✅ Registered %s binary sensors", DOMAIN, len(sensors))


class TuyaCloudBinarySensor(BinarySensorEntity):
    """Tuya Cloud Custom Binary Sensor with type+translate."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = False

        attrs = build_entity_attrs(device, dp, "binary_sensor")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")

        # ✅ Binary sensor is always boolean type by design
        self._translated = dp.get("translated", {})

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered binary sensor entity: %s", DOMAIN, key)

    @property
    def is_on(self):
        """Return True if binary sensor is ON."""
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_update(self):
        """No polling — push only."""
        pass

    async def async_update_from_status(self, value):
        """Update from Status manager with translate support."""
        try:
            parsed = bool(value)

            parsed_str = str(int(parsed))  # for translated keys if needed: 0/1
            if self._translated:
                translated = (
                    self._translated.get(parsed)
                    or self._translated.get(parsed_str)
                    or parsed
                )
                _LOGGER.debug(
                    "[%s] ⚙️ Binary Sensor %s: raw=%s | parsed=%s | translate_keys=%s | final=%s",
                    DOMAIN,
                    self._attr_unique_id,
                    value,
                    parsed,
                    list(self._translated.keys()),
                    translated
                )
                self._state = bool(translated) if isinstance(translated, bool) else bool(parsed)
            else:
                self._state = parsed

        except (TypeError, ValueError) as e:
            _LOGGER.exception("[%s] ❌ Failed to parse binary sensor value: %s", DOMAIN, e)
            self._state = False

        self.async_write_ha_state()

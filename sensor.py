"""Tuya Cloud Custom - Robust Sensor platform with translate support."""

import logging
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom sensors."""
    devices = hass.data[DOMAIN]["devices"]
    sensors = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudSensor(hass, device, dp))
    async_add_entities(sensors)
    _LOGGER.info("[%s] ✅ Registered %s sensors", DOMAIN, len(sensors))


class TuyaCloudSensor(SensorEntity):
    """Tuya Cloud Custom Sensor with type+translate."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None

        attrs = build_entity_attrs(device, dp, "sensor")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")
        self._attr_native_unit_of_measurement = attrs.get("native_unit_of_measurement")
        if "icon" in attrs:
            self._attr_icon = attrs["icon"]

        # ✅ Type and translate map
        self._dp_type = dp.get("type", "string")
        self._translated = dp.get("translated", {})

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered sensor entity: %s", DOMAIN, key)

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_update(self):
        """No polling — push only."""
        pass

    async def async_update_from_status(self, value):
        """Update from Status manager with translate for all types and detailed debug."""
        try:
            parsed = value
            if self._dp_type == "boolean":
                parsed = bool(value)
            elif self._dp_type == "integer":
                parsed = int(value)
            elif self._dp_type == "float":
                parsed = float(value)
            elif self._dp_type == "bitfield":
                parsed = int(value)
            else:
                parsed = str(value)

            # ✅ Normalize to string for translation lookup for consistent matching
            parsed_str = str(parsed)
            if self._translated:
                # Try exact match int first, then string fallback from yaml
                translated = (
                    self._translated.get(parsed)
                    or self._translated.get(parsed_str)
                    or parsed
                )

                _LOGGER.debug(
                    "[%s] ⚙️ Sensor %s: raw=%s | parsed=%s | translate_keys=%s | final=%s",
                    DOMAIN,
                    self._attr_unique_id,
                    value,
                    parsed,
                    list(self._translated.keys()),
                    translated
                )
                self._state = translated
            else:
                self._state = parsed

        except (TypeError, ValueError) as e:
            _LOGGER.exception("[%s] ❌ Failed to parse sensor value: %s", DOMAIN, e)
            self._state = value

        self.async_write_ha_state()

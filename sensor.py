"""Tuya Cloud Custom - Sensor platform."""

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
    """Tuya Cloud Custom Sensor."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None

        # Standard attributes
        attrs = build_entity_attrs(device, dp, "sensor")
        self._attr_unique_id = attrs["unique_id"]
        self._attr_has_entity_name = False

        if "name" in attrs:
            self._attr_name = attrs["name"]

        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")
        self._attr_native_unit_of_measurement = attrs.get("native_unit_of_measurement")

        # ✅ Store explicit type if present
        self._dp_type = dp.get("type", "string")

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
        """Update from Status manager with proper type handling."""
        dp_type = self._dp_type  # already stored in __init__ as lowercase
        raw = value

        try:
            if dp_type == "boolean":
                self._state = bool(raw)
            elif dp_type in ("integer", "bitfield"):
                self._state = int(raw)
            elif dp_type == "float":
                self._state = float(raw)
            elif dp_type in ("enum", "string"):
                self._state = str(raw)
            else:
                self._state = raw  # fallback
        except (TypeError, ValueError):
            self._state = raw

        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()


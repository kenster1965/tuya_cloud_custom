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

        # Build standardized attributes
        attrs = build_entity_attrs(device, dp, "sensor")
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        if "device_class" in attrs:
            self._attr_device_class = attrs["device_class"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        # ✅ CRITICAL: Use correct native unit key for HA
        if "native_unit_of_measurement" in attrs:
            self._attr_native_unit_of_measurement = attrs["native_unit_of_measurement"]

        # Register for live status updates
        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self
        _LOGGER.debug("[%s] Registered sensor entity: %s", DOMAIN, key)


    @property
    def native_value(self):
        return self._state


    @property
    def device_info(self):
        """Attach to parent device registry entry."""
        return build_device_info(self._device)


    async def async_update_from_status(self, val):
        """Update sensor from status payload, with type handling."""
        if self._dp.get("integer"):
            try:
                self._state = int(val)
            except (ValueError, TypeError):
                self._state = val
        else:
            try:
                self._state = float(val)
            except (ValueError, TypeError):
                self._state = val

        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()


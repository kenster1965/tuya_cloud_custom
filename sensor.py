"""
Tuya Cloud Custom: Sensor Platform
----------------------------------
Defines sensor entities linked to Tuya Cloud DP values.
"""

import logging

from homeassistant.components.sensor import SensorEntity

from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom sensors from config entry."""

    devices = hass.data[DOMAIN]["devices"]
    sensors = []

    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudSensor(device, dp, hass, _LOGGER))

    async_add_entities(sensors)


class TuyaCloudSensor(SensorEntity):
    """Tuya Cloud Custom Sensor Entity."""

    def __init__(self, device, dp, hass, logger):
        self._hass = hass
        self._device = device
        self._dp = dp

        attrs = build_entity_attrs(device, dp, "sensor", logger=logger)

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]
        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")
        self._attr_native_unit_of_measurement = attrs.get("unit")
        self._state = None

        # Register this entity for status updates
        device_id = device["tuya_device_id"]
        code = dp["code"]
        key = (device_id, code)
        logger.debug(f"[{DOMAIN}] Registering sensor entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def native_value(self):
        """Return current sensor value."""
        return self._state

    @property
    def device_info(self):
        """Link to Device Registry."""
        return build_device_info(self._device)

    async def async_update(self):
        """HA calls this if polling, but our status updater pushes state live."""
        pass  # No manual polling: Status class updates us automatically

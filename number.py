"""
Tuya Cloud Custom: Number Platform
----------------------------------
Defines number entities linked to Tuya Cloud DP values.
"""

import logging
from homeassistant.components.number import NumberEntity

from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom numbers from config entry."""

    devices = hass.data[DOMAIN]["devices"]
    numbers = []

    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "number" and dp.get("enabled", True):
                numbers.append(TuyaCloudNumber(device, dp, hass, _LOGGER))

    async_add_entities(numbers)


class TuyaCloudNumber(NumberEntity):
    """Tuya Cloud Custom Number Entity."""

    def __init__(self, device, dp, hass, logger):
        self._hass = hass
        self._device = device
        self._dp = dp

        attrs = build_entity_attrs(device, dp, "number", logger=logger)

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]
        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")
        self._attr_native_min_value = attrs.get("min")
        self._attr_native_max_value = attrs.get("max")
        self._attr_native_step = attrs.get("step")

        self._state = None

        # Register for status updates
        device_id = device["tuya_device_id"]
        code = dp["code"]
        key = (device_id, code)
        logger.debug(f"[{DOMAIN}] Registering number entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_native_value(self, value):
        _LOGGER.warning(f"[{DOMAIN}] ✅ TODO: Implement async_set_native_value for {self._attr_name} to {value}")
        # 🔑 This is where you'd call Tuya Cloud to set DP value.

    async def async_update(self):
        pass  # Status pushes live updates

"""Tuya Cloud Custom - Number platform."""

import logging
from homeassistant.components.number import NumberEntity
from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info
from .helpers.token_refresh import send_tuya_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom numbers."""
    devices = hass.data[DOMAIN]["devices"]
    numbers = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "number" and dp.get("enabled", True):
                numbers.append(TuyaCloudNumber(hass, device, dp))
    async_add_entities(numbers)
    _LOGGER.info("[%s] ✅ Registered %s numbers", DOMAIN, len(numbers))


class TuyaCloudNumber(NumberEntity):
    """Representation of a Tuya Cloud Custom Number."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None

        # Standardized attributes
        attrs = build_entity_attrs(device, dp, "number")
        self._attr_unique_id = attrs["unique_id"]
        self._attr_has_entity_name = False
        if "name" in attrs:
            self._attr_name = attrs["name"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        self._attr_native_min_value = dp.get("min_value", 0)
        self._attr_native_max_value = dp.get("max_value", 100)
        self._attr_native_step = dp.get("step_size", 1)

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self
        _LOGGER.debug("[%s] ✅ Registered number entity: %s", DOMAIN, key)

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_native_value(self, value: float):
        """Send number value command."""
        response = await self._hass.async_add_executor_job(
            send_tuya_command,
            self._hass,
            self._device["tuya_device_id"],
            self._dp["code"],
            value
        )
        if response and response.status_code == 200:
            self._state = value
            self.async_write_ha_state()

    async def async_update(self):
        """No direct polling — status.py pushes updates."""
        pass

    async def async_update_from_status(self, val):
        """Update from poller."""
        try:
            self._state = float(val)
        except (TypeError, ValueError):
            self._state = val
        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()

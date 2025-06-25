"""Tuya Cloud Custom - Number platform."""

import logging
from homeassistant.components.number import NumberEntity
from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info
from .helpers.tuya_command import send_tuya_command

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

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        self._attr_native_min_value = dp.get("min_value", 0)
        self._attr_native_max_value = dp.get("max_value", 100)
        self._attr_native_step = dp.get("step_size", 1)

        self._dp_type = dp.get("type", "float")
        self._is_passive = dp.get("is_passive_entity", False)

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self
        _LOGGER.debug("[%s] ✅ Registered number entity: %s | Passive=%s", DOMAIN, key, self._is_passive)

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_native_value(self, value: float):
        """Send number value command with explicit DP type."""

        if self._is_passive:
            _LOGGER.info("[%s] 🚫 Number %s is passive — command not sent", DOMAIN, self._attr_unique_id)
            self._state = value
            self.async_write_ha_state()
            return

        # ✅ Cast safely before sending
        if self._dp_type == "integer":
            value_to_send = int(value)
        elif self._dp_type == "float":
            value_to_send = float(value)
        else:
            value_to_send = value

        response = await self._hass.async_add_executor_job(
            send_tuya_command,
            self._hass,
            self._device["tuya_device_id"],
            self._dp["code"],
            value_to_send
        )
        if response and response.status_code == 200:
            self._state = value_to_send
            self.async_write_ha_state()

    async def async_update(self):
        """No polling — status pushes updates."""
        pass

    async def async_update_from_status(self, val):
        """Update from status manager with type-safe parsing."""
        try:
            if self._dp_type == "integer":
                self._state = int(val)
            elif self._dp_type == "float":
                self._state = float(val)
            else:
                self._state = val
        except (TypeError, ValueError):
            self._state = val

        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()

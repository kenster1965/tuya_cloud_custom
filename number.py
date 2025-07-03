"""Tuya Cloud Custom - Number platform."""

import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.restore_state import RestoreEntity

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


class TuyaCloudNumber(NumberEntity, RestoreEntity):
    """Representation of a Tuya Cloud Custom Number."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None
        self._last_sent_value = None
        self._restored_once = False

        attrs = build_entity_attrs(device, dp, "number")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_entity_category = attrs.get("entity_category")
        self._attr_icon = attrs.get("icon")

        self._attr_native_min_value = dp.get("min_value", 0)
        self._attr_native_max_value = dp.get("max_value", 100)
        self._attr_native_step = dp.get("step_size", 1)

        self._dp_type = dp.get("type", "float")
        self._is_passive = dp.get("is_passive_entity", False)
        self._restore_on_reconnect = dp.get("restore_on_reconnect", False)

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered number entity: %s | Passive=%s | Restore=%s",
                      DOMAIN, key, self._is_passive, self._restore_on_reconnect)

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_native_value(self, value: float):
        """Send number value command with explicit DP type."""

        if self._is_passive:
            _LOGGER.info("[%s] 🚫 Passive number '%s' — ignoring command: %s",
                         DOMAIN, self._attr_unique_id, value)
            self._state = value
            self.async_write_ha_state()
            return

        # Type casting
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
            self._last_sent_value = value_to_send
            self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Restore value from previous HA state on reconnect, if configured."""
        if (
            self._restore_on_reconnect
            and not self._is_passive
            and not self._restored_once
        ):
            last_state = await self.async_get_last_state()
            if last_state and last_state.state not in (None, "unknown", "unavailable"):
                try:
                    if self._dp_type == "integer":
                        restored = int(last_state.state)
                    elif self._dp_type == "float":
                        restored = float(last_state.state)
                    else:
                        restored = last_state.state

                    _LOGGER.info("[%s] ♻️ Restoring number '%s' to %s (restore_on_reconnect)",
                                 DOMAIN, self._attr_unique_id, restored)

                    await self._hass.async_add_executor_job(
                        send_tuya_command,
                        self._hass,
                        self._device["tuya_device_id"],
                        self._dp["code"],
                        restored
                    )

                    self._state = restored
                    self._last_sent_value = restored
                    self._restored_once = True
                    self.async_write_ha_state()

                except Exception as e:
                    _LOGGER.warning("[%s] ❌ Failed to restore number '%s': %s",
                                    DOMAIN, self._attr_unique_id, e)

    async def async_update(self):
        """No polling — status pushes updates."""
        pass

    async def async_update_from_status(self, val):
        """Update from status manager with type-safe parsing."""
        try:
            if self._dp_type == "integer":
                parsed = int(val)
            elif self._dp_type == "float":
                parsed = float(val)
            else:
                parsed = val

            self._state = parsed

        except (TypeError, ValueError):
            self._state = val

        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()

"""Tuya Cloud Custom - Switch platform."""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info
from .helpers.tuya_command import send_tuya_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches."""
    devices = hass.data[DOMAIN]["devices"]
    switches = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(hass, device, dp))
    async_add_entities(switches)
    _LOGGER.info("[%s] ✅ Registered %s switches", DOMAIN, len(switches))


class TuyaCloudSwitch(SwitchEntity, RestoreEntity):
    """Representation of a Tuya Cloud Custom Switch."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        self._state = False
        self._last_ha_command = None
        self._restored_once = False

        attrs = build_entity_attrs(device, dp, "switch")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._dp_type = dp.get("type", "boolean")
        self._is_passive = dp.get("is_passive_entity", False)
        self._restore_on_reconnect = dp.get("restore_on_reconnect", False)

        self._attr_entity_category = attrs.get("entity_category")
        self._attr_icon = attrs.get("icon")

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self
        _LOGGER.debug("[%s] ✅ Registered switch entity: %s | Passive: %s | Restore: %s",
                      DOMAIN, key, self._is_passive, self._restore_on_reconnect)

    @property
    def is_on(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_turn_on(self, **kwargs):
        await self._send_tuya_command(True)

    async def async_turn_off(self, **kwargs):
        await self._send_tuya_command(False)

    async def _send_tuya_command(self, state):
        """Send switch command with correct DP type."""
        if self._is_passive:
            _LOGGER.info("[%s] 🚫 Passive switch '%s' — ignoring command: %s",
                         DOMAIN, self._attr_unique_id, state)
            return

        try:
            if self._dp_type == "boolean":
                value = bool(state)
            elif self._dp_type == "integer":
                value = int(state)
            elif self._dp_type == "float":
                value = float(state)
            elif self._dp_type == "enum":
                value = str(state).lower()
            else:
                value = state

            response = await self._hass.async_add_executor_job(
                send_tuya_command,
                self._hass,
                self._device["tuya_device_id"],
                self._dp["code"],
                value
            )

            if response and response.status_code == 200:
                self._state = bool(state)
                self._last_ha_command = self._state
                self.async_write_ha_state()

        except Exception as e:
            _LOGGER.warning("[%s] ❌ Switch command failed for %s: %s", DOMAIN, self._attr_unique_id, e)

    async def async_added_to_hass(self):
        """Handle entity addition and optional state restore."""
        if self._restore_on_reconnect and not self._is_passive and not self._restored_once:
            last_state = await self.async_get_last_state()
            if last_state and last_state.state in ("on", "off"):
                restored_state = last_state.state == "on"
                _LOGGER.info("[%s] 🔁 Restoring '%s' to %s (restore_on_reconnect)",
                             DOMAIN, self._attr_unique_id, restored_state)
                await self._send_tuya_command(restored_state)
                self._restored_once = True

    async def async_update(self):
        """No polling — status pushes updates."""
        pass

    async def async_update_from_status(self, val):
        """Update from status manager with DP type."""
        try:
            if self._dp_type == "boolean":
                self._state = bool(val)
            elif self._dp_type == "integer":
                self._state = bool(int(val))
            elif self._dp_type == "float":
                self._state = bool(float(val))
            elif self._dp_type == "enum":
                self._state = str(val).lower() not in ("off", "false", "0")
            else:
                self._state = bool(val)
        except Exception as e:
            _LOGGER.warning("[%s] ⚠️ Switch type cast error: %s", DOMAIN, e)
            self._state = bool(val)

        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()

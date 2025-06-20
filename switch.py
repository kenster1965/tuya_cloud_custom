"""Tuya Cloud Custom - Switch platform."""

import logging
from homeassistant.components.switch import SwitchEntity
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


class TuyaCloudSwitch(SwitchEntity):
    """Representation of a Tuya Cloud Custom Switch."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = False

        # Standardized attributes
        attrs = build_entity_attrs(device, dp, "switch")
        self._attr_unique_id = attrs["unique_id"]
        self._attr_has_entity_name = False  # use unique_id for Entity ID only
        if "name" in attrs:
            self._attr_name = attrs["name"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self
        _LOGGER.debug("[%s] ✅ Registered switch entity: %s", DOMAIN, key)

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

    async def _send_tuya_command(self, state: bool):
        """Send switch command safely using helper."""
        response = await self._hass.async_add_executor_job(
            send_tuya_command,
            self._hass,
            self._device["tuya_device_id"],
            self._dp["code"],
            state
        )
        if response and response.status_code == 200:
            self._state = state
            self.async_write_ha_state()

    async def async_update(self):
        """No direct polling — status.py pushes updates."""
        pass

    async def async_update_from_status(self, val):
        """Update from poller."""
        self._state = bool(val)
        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()

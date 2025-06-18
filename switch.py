"""
Tuya Cloud Custom: Switch Platform
----------------------------------
Defines switch entities linked to Tuya Cloud DP values.
"""

import logging
from homeassistant.components.switch import SwitchEntity

from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches from config entry."""

    devices = hass.data[DOMAIN]["devices"]
    switches = []

    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(device, dp, hass, _LOGGER))

    async_add_entities(switches)


class TuyaCloudSwitch(SwitchEntity):
    """Tuya Cloud Custom Switch Entity."""

    def __init__(self, device, dp, hass, logger):
        self._hass = hass
        self._device = device
        self._dp = dp

        attrs = build_entity_attrs(device, dp, "switch", logger=logger)

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]
        self._state = False

        # Register for status updates
        device_id = device["tuya_device_id"]
        code = dp["code"]
        key = (device_id, code)
        logger.debug(f"[{DOMAIN}] Registering switch entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def is_on(self):
        return bool(self._state)

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_turn_on(self, **kwargs):
        _LOGGER.warning(f"[{DOMAIN}] ✅ TODO: Implement async_turn_on for {self._attr_name}")
        # 🔑 This is where you'd call the Tuya Cloud set API for DP value.

    async def async_turn_off(self, **kwargs):
        _LOGGER.warning(f"[{DOMAIN}] ✅ TODO: Implement async_turn_off for {self._attr_name}")
        # 🔑 This is where you'd call the Tuya Cloud set API for DP value.

    async def async_update(self):
        pass  # No polling: Status class pushes updates

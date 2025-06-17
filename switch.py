import logging
from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN
from homeassistant.components.switch import SwitchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches."""
    devices = hass.data[DOMAIN]["devices"]
    switches = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(device, dp, hass))
    async_add_entities(switches)


class TuyaCloudSwitch(SwitchEntity):
    """Tuya Cloud Custom Switch."""

    def __init__(self, device, dp, hass):
        logger = logging.getLogger(__name__)
        attrs = build_entity_attrs(device, dp, "switch", logger=logger)

        self._device = device
        self._dp = dp
        self._hass = hass

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        self._state = False  # switches use bool

        # Link to TuyaStatus key
        self._tuya_device_id = device["tuya_device_id"]
        self._tuya_code = dp["code"]

        key = (self._tuya_device_id, self._tuya_code)
        logger.debug(f"[{DOMAIN}] Registering switch entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def is_on(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_turn_on(self, **kwargs):
        # 🔧 TODO: Implement API call to Tuya Cloud to switch ON
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        # 🔧 TODO: Implement API call to Tuya Cloud to switch OFF
        self._state = False
        self.async_write_ha_state()

    async def async_update(self):
        # No direct poll — TuyaStatus sets _state
        pass

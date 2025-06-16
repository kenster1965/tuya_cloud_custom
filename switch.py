from homeassistant.components.switch import SwitchEntity
from . import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    devices = hass.data[DOMAIN]["devices"]

    switches = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp["platform"] == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(device, dp))

    async_add_entities(switches)

class TuyaCloudSwitch(SwitchEntity):
    def __init__(self, device, dp):
        self._device = device
        self._dp = dp
        self._attr_name = f"{device['friendly_name']} - {dp['friendly_name']}"
        self._attr_unique_id = f"{device['ha_name']}_{dp['code']}"
        self._state = False

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        # TODO: Send Tuya cloud command
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        # TODO: Send Tuya cloud command
        self._state = False
        self.async_write_ha_state()

    async def async_update(self):
        # TODO: Poll status
        pass

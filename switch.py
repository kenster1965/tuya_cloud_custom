from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches from config entry."""

    devices = hass.data[DOMAIN]["devices"]

    switches = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(device, dp))

    async_add_entities(switches)


class TuyaCloudSwitch(SwitchEntity):
    """Representation of a Tuya Cloud Custom Switch."""

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
        self._state = True
        self.async_write_ha_state()
        # TODO: Send Tuya Cloud command here

    async def async_turn_off(self, **kwargs):
        self._state = False
        self.async_write_ha_state()
        # TODO: Send Tuya Cloud command here

    async def async_update(self):
        # TODO: Optionally update self._state from Tuya Cloud
        pass

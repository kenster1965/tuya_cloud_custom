from .helpers.helper import build_entity_attrs
from .const import DOMAIN
from homeassistant.components.switch import SwitchEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches from config entry."""
    devices = hass.data[DOMAIN]["devices"]
    switches = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(device, dp, hass))
    async_add_entities(switches)


class TuyaCloudSwitch(SwitchEntity):
    """Tuya Cloud Custom Switch."""

    def __init__(self, device, dp):
        attrs = build_entity_attrs(device, dp, "switch", logger=hass.components.logger)

        self._device = device
        self._dp = dp
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        self._state = False


    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state = True
        self.async_write_ha_state()
        # 🔧 TODO: Add real Tuya API call to turn on
        # e.g., await send_tuya_command(self._device, self._dp['code'], True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._state = False
        self.async_write_ha_state()
        # 🔧 TODO: Add real Tuya API call to turn off
        # e.g., await send_tuya_command(self._device, self._dp['code'], False)

    async def async_update(self):
        """Update the switch state from the cloud (optional)."""
        # 🔧 TODO: Add real polling logic if needed
        pass

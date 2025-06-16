from homeassistant.components.number import NumberEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom numbers from config entry."""

    devices = hass.data[DOMAIN]["devices"]

    numbers = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "number" and dp.get("enabled", True):
                numbers.append(TuyaCloudNumber(device, dp))

    async_add_entities(numbers)


class TuyaCloudNumber(NumberEntity):
    """Representation of a Tuya Cloud Custom Number."""

    def __init__(self, device, dp):
        self._device = device
        self._dp = dp
        self._attr_name = f"{device['friendly_name']} - {dp['friendly_name']}"
        self._attr_unique_id = f"{device['ha_name']}_{dp['code']}"
        self._value = float(dp.get("dps_default_value", 0))
        self._attr_native_min_value = dp.get("min_value", 0)
        self._attr_native_max_value = dp.get("max_value", 100)
        self._attr_native_step = dp.get("step_size", 1.0)

    @property
    def native_value(self):
        return self._value

    async def async_set_native_value(self, value):
        self._value = value
        self.async_write_ha_state()
        # TODO: Send to Tuya Cloud here

    async def async_update(self):
        # TODO: Poll actual Tuya value if needed
        pass

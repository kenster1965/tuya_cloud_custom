from .helpers.helper import build_entity_attrs
from .const import DOMAIN
from homeassistant.components.number import NumberEntity

async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = hass.data[DOMAIN]["devices"]
    numbers = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "number" and dp.get("enabled", True):
                numbers.append(TuyaCloudNumber(device, dp, hass))
    async_add_entities(numbers)


class TuyaCloudNumber(NumberEntity):
    """Tuya Cloud Custom Number."""

    def __init__(self, device, dp):
        attrs = build_entity_attrs(device, dp, "number", logger=hass.components.logger)

        self._device = device
        self._dp = dp
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_native_min_value = attrs.get("min", 0)
        self._attr_native_max_value = attrs.get("max", 100)
        self._attr_native_step = attrs.get("step", 1)

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        self._value = dp.get("dps_default_value", 0)

    @property
    def native_value(self):
        return self._value

    async def async_set_native_value(self, value):
        """Send new value to Tuya and update local state."""
        self._value = value
        self.async_write_ha_state()
        # 🔧 TODO: Send to Tuya cloud
        # await send_tuya_command(self._device, self._dp['code'], value)

    async def async_update(self):
        """Poll for updated value (optional)."""
        # 🔧 TODO: Add real polling logic if needed
        pass

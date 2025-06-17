import logging
from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN
from homeassistant.components.number import NumberEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom numbers."""
    devices = hass.data[DOMAIN]["devices"]
    numbers = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "number" and dp.get("enabled", True):
                numbers.append(TuyaCloudNumber(device, dp, hass))
    async_add_entities(numbers)


class TuyaCloudNumber(NumberEntity):
    """Tuya Cloud Custom Number."""

    def __init__(self, device, dp, hass):
        logger = logging.getLogger(__name__)
        attrs = build_entity_attrs(device, dp, "number", logger=logger)

        self._device = device
        self._dp = dp
        self._hass = hass

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_native_min_value = attrs.get("min", 0)
        self._attr_native_max_value = attrs.get("max", 100)
        self._attr_native_step = attrs.get("step", 1)

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        self._value = None

        # Link to TuyaStatus key
        self._tuya_device_id = device["tuya_device_id"]
        self._tuya_code = dp["code"]

        key = (self._tuya_device_id, self._tuya_code)
        logger.debug(f"[{DOMAIN}] Registering number entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def native_value(self):
        return self._value

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_native_value(self, value: float):
        # 🔧 TODO: Implement API call to Tuya Cloud to set number value
        self._value = value
        self.async_write_ha_state()

    async def async_update(self):
        # No direct poll — TuyaStatus sets _value
        pass

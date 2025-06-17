import logging
from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN
from homeassistant.components.sensor import SensorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom sensors."""
    devices = hass.data[DOMAIN]["devices"]
    sensors = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudSensor(device, dp, hass))
    async_add_entities(sensors)


class TuyaCloudSensor(SensorEntity):
    """Tuya Cloud Custom Sensor."""

    def __init__(self, device, dp, hass):
        logger = logging.getLogger(__name__)
        attrs = build_entity_attrs(device, dp, "sensor", logger=logger)

        self._device = device
        self._dp = dp
        self._hass = hass

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        if "device_class" in attrs:
            self._attr_device_class = attrs["device_class"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        if "unit" in attrs:
            self._attr_native_unit_of_measurement = attrs["unit"]

        self._state = None

        # Link to TuyaStatus key
        self._tuya_device_id = device["tuya_device_id"]
        self._tuya_code = dp["code"]

        key = (self._tuya_device_id, self._tuya_code)
        logger.debug(f"[{DOMAIN}] Registering sensor entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        """Link this entity to a Device in HA."""
        return build_device_info(self._device)

    async def async_update(self):
        # No direct poll — handled by TuyaStatus loop.
        pass

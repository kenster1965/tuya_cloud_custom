from .helpers.helper import build_entity_attrs
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = hass.data[DOMAIN]["devices"]
    sensors = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudSensor(device, dp, hass))
    async_add_entities(sensors)


class TuyaCloudSensor(SensorEntity):
    """Tuya Cloud Custom Sensor."""

    def __init__(self, device, dp):
        attrs = build_entity_attrs(device, dp, "sensor", logger=hass.components.logger)

        self._device = device
        self._dp = dp
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        if "device_class" in attrs:
            self._attr_device_class = attrs["device_class"]

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        if "unit" in attrs:
            self._attr_native_unit_of_measurement = attrs["unit"]

        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        # 🔧 TODO: Add real polling logic
        pass

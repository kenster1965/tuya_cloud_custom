from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom sensors from config entry."""

    devices = hass.data[DOMAIN]["devices"]

    sensors = []
    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudSensor(device, dp))

    async_add_entities(sensors)


class TuyaCloudSensor(SensorEntity):
    """Representation of a Tuya Cloud Custom Sensor."""

    def __init__(self, device, dp):
        self._device = device
        self._dp = dp
        self._attr_name = f"{device['friendly_name']} - {dp['friendly_name']}"
        self._attr_unique_id = f"{device['ha_name']}_{dp['code']}"
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        # TODO: Poll actual Tuya value if needed
        pass

"""Tuya Cloud Custom - Robust Binary Sensor platform with on_value support."""

import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom binary sensors."""
    devices = hass.data[DOMAIN]["devices"]
    sensors = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "binary_sensor" and dp.get("enabled", True):
                sensors.append(TuyaCloudBinarySensor(hass, device, dp))
    async_add_entities(sensors)
    _LOGGER.info("[%s] ✅ Registered %s binary sensors", DOMAIN, len(sensors))


class TuyaCloudBinarySensor(BinarySensorEntity):
    """Tuya Cloud Custom Binary Sensor with robust on_value logic."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = False

        attrs = build_entity_attrs(device, dp, "binary_sensor")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")
        if "icon" in attrs:
            self._attr_icon = attrs["icon"]

        # ✅ Read on_value; default to True if not specified
        self._on_value = dp.get("on_value", True)

        # Optional: store type if needed for debug
        self._dp_type = dp.get("type", "boolean")

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered binary sensor entity: %s | on_value=%s", DOMAIN, key, self._on_value)

    @property
    def is_on(self):
        """Return True if binary sensor is ON."""
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_update(self):
        """No polling — push only."""
        pass

    async def async_update_from_status(self, value):
        """Update state using on_value pattern."""
        try:
            parsed = value

            # ✅ Robust compare for any DP type
            if isinstance(parsed, (bool, int, float)):
                is_on = parsed == self._on_value
            else:
                is_on = str(parsed) == str(self._on_value)

            self._state = is_on

            _LOGGER.debug(
                "[%s] ⚙️ Binary Sensor %s: raw=%s | on_value=%s | is_on=%s",
                DOMAIN,
                self._attr_unique_id,
                value,
                self._on_value,
                is_on
            )

        except Exception as e:
            _LOGGER.exception("[%s] ❌ Failed to parse binary sensor value: %s", DOMAIN, e)
            self._state = False

        self.async_write_ha_state()

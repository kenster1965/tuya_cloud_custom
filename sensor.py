"""Tuya Cloud Custom - Robust Sensor platform with translate + mirror support."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_state_change
from homeassistant.const import STATE_UNKNOWN

from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Initialize Tuya Cloud Custom sensors."""
    devices = hass.data[DOMAIN]["devices"]
    sensors = []

    for device in devices:
        for dp in device.get("entities", []):
            if not dp.get("enabled", True):
                continue

            # Handle mirrored climate sensor
            if dp.get("mirrored", False):
                if "from_climate" in dp and "from_entity" in dp:
                    try:
                        sensors.append(MirroredClimateSensor(hass, device, dp))
                        _LOGGER.info("[%s] ➕ Registered mirrored climate sensor: %s", DOMAIN, dp)
                    except Exception as e:
                        _LOGGER.warning("[%s] ❌ Failed to create mirrored sensor: %s", DOMAIN, e)
                else:
                    _LOGGER.warning("[%s] ❌ Skipped mirrored sensor due to missing config: %s", DOMAIN, dp)

            # Handle regular Tuya sensor
            elif dp.get("platform") == "sensor":
                try:
                    sensors.append(TuyaCloudSensor(hass, device, dp))
                except Exception as e:
                    _LOGGER.warning("[%s] ❌ Failed to create sensor: %s", DOMAIN, e)

    async_add_entities(sensors)
    _LOGGER.info("[%s] ✅ Registered %s sensors", DOMAIN, len(sensors))


class TuyaCloudSensor(SensorEntity):
    """Tuya Cloud sensor with optional value translation."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None

        attrs = build_entity_attrs(device, dp, "sensor")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]
        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("entity_category")
        self._attr_native_unit_of_measurement = attrs.get("native_unit_of_measurement")
        self._attr_icon = attrs.get("icon")

        self._dp_type = dp.get("type", "string")
        self._translated = dp.get("translated", {})

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered Tuya sensor entity: %s", DOMAIN, key)

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_update(self):
        """Polling not used; Tuya uses push updates."""
        pass

    async def async_update_from_status(self, value):
        """Update state from Tuya push status."""
        try:
            parsed = self._parse_value(value)
            translated = self._translate(parsed)
            self._state = translated
        except Exception as e:
            _LOGGER.exception("[%s] ❌ Failed to parse sensor value: %s", DOMAIN, e)
            self._state = value

        self.async_write_ha_state()

    def _parse_value(self, value):
        if self._dp_type == "boolean":
            return bool(value)
        elif self._dp_type == "integer":
            return int(value)
        elif self._dp_type == "float":
            return float(value)
        elif self._dp_type == "bitfield":
            return int(value)
        return str(value)

    def _translate(self, parsed):
        parsed_str = str(parsed)
        return (
            self._translated.get(parsed)
            or self._translated.get(parsed_str)
            or parsed
        )


class MirroredClimateSensor(SensorEntity):
    """A read-only sensor that mirrors a climate attribute like current_temperature."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None

        device_slug = device["friendly_name"].lower().replace(" ", "_")
        climate_slug = dp["from_climate"]
        self._source_entity_id = f"climate.{device_slug}_{climate_slug}"
        self._from_attr = dp["from_entity"]

        self._attr_name = f"{dp['from_climate'].replace('_', ' ').title()} {dp['from_entity'].replace('_', ' ').title()}"
        self._attr_unique_id = f"{device['tuya_device_id']}_{dp['from_climate']}_{dp['from_entity']}_mirror"
        self._attr_device_class = dp.get("device_class", "temperature")
        self._attr_native_unit_of_measurement = dp.get("unit_of_measurement")
        self._attr_state_class = "measurement"
        self._attr_should_poll = False

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_added_to_hass(self):
        """Attach state tracking from the source climate entity."""
        async def _update(entity_id, old_state, new_state):
            if not new_state or new_state.state in (None, STATE_UNKNOWN):
                return
            try:
                new_val = new_state.attributes.get(self._from_attr)
                _LOGGER.debug("[%s] 🔁 Mirrored sensor update from %s.%s: %s", DOMAIN, entity_id, self._from_attr, new_val)
                if isinstance(new_val, (int, float)):
                    self._state = new_val
                    self.async_write_ha_state()
                else:
                    _LOGGER.debug("[%s] 🚫 Ignored non-numeric mirrored value: %s", DOMAIN, new_val)
            except Exception as e:
                _LOGGER.warning("[%s] ⚠️ Failed to update mirrored sensor: %s", DOMAIN, e)

        async_track_state_change(self._hass, self._source_entity_id, _update)

    async def async_update(self):
        """Polling not used for mirrored sensor."""
        pass

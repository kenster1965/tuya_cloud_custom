"""Tuya Cloud Custom - Climate platform."""

import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .helpers.helper import build_device_info
from .helpers.tuya_command import send_tuya_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom climate entities."""
    devices = hass.data[DOMAIN]["devices"]
    climates = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "climate" and dp.get("enabled", True):
                climates.append(TuyaCloudClimate(hass, device, dp))
    async_add_entities(climates)
    _LOGGER.info("[%s] ✅ Registered %s climates", DOMAIN, len(climates))


class TuyaCloudClimate(ClimateEntity):
    """Representation of a Tuya Cloud Custom Climate."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        self._attr_unique_id = dp.get("unique_id")
        self._attr_has_entity_name = False

        self._current_temp = None
        self._target_temp = None
        self._mode_value = None
        self._switch_state = None

        self._has_switch = bool(dp.get("switch_code"))

        self._modes_map = dp.get("hvac_modes", {})
        self._attr_hvac_modes = list(self._modes_map.keys())

        yaml_unit = dp.get("temperature_unit", "C")
        self._attr_temperature_unit = (
            UnitOfTemperature.FAHRENHEIT if yaml_unit.upper() in ("F", "°F") else UnitOfTemperature.CELSIUS
        )
        self._attr_min_temp = dp.get("min_temp", 10.0)
        self._attr_max_temp = dp.get("max_temp", 35.0)
        self._attr_precision = dp.get("precision", 1.0)

        # Store explicit DP types
        self._current_temp_type = dp.get("current_temperature_type", "float")
        self._target_temp_type = dp.get("target_temperature_type", "float")
        self._mode_type = dp.get("hvac_modes_type", "enum")
        self._switch_type = dp.get("switch_type", "boolean")

        tid = device["tuya_device_id"]
        for code in [
            dp["current_temperature_code"],
            dp["target_temperature_code"],
            dp["hvac_modes_code"],
            dp.get("switch_code")
        ]:
            if code:
                hass.data[DOMAIN]["entities"][(tid, code)] = self

        _LOGGER.debug("[%s] ✅ Registered climate entity: %s", DOMAIN, self._attr_unique_id)

    @property
    def device_info(self):
        return build_device_info(self._device)

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def hvac_mode(self):
        """Resolve HVAC mode based on Tuya switch + mode value."""
        if self._has_switch and not self._switch_state:
            return HVACMode.OFF

        for ha_mode, tuya_val in self._modes_map.items():
            if self._mode_value == tuya_val:
                return ha_mode

        # Fallback
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs):
        """Send target temperature."""
        new_temp = kwargs.get("temperature")
        if new_temp is None:
            return

        value = new_temp
        if self._target_temp_type == "float":
            value = float(new_temp)
        elif self._target_temp_type == "integer":
            value = int(new_temp)
        # Many Tuya climates expect *10
        value = int(value * 10)

        resp = await self._hass.async_add_executor_job(
            send_tuya_command,
            self._hass,
            self._device["tuya_device_id"],
            self._dp["target_temperature_code"],
            value
        )
        if resp and resp.status_code == 200:
            self._target_temp = new_temp
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Change HVAC mode & optional switch."""
        tid = self._device["tuya_device_id"]

        mode_val = self._modes_map.get(hvac_mode)
        if mode_val is not None:
            await self._hass.async_add_executor_job(
                send_tuya_command,
                self._hass,
                tid,
                self._dp["hvac_modes_code"],
                mode_val
            )

        if self._has_switch:
            switch_val = hvac_mode != HVACMode.OFF
            await self._hass.async_add_executor_job(
                send_tuya_command,
                self._hass,
                tid,
                self._dp["switch_code"],
                switch_val
            )

        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_update(self):
        """No polling — status pushes updates."""
        pass

    async def async_update_from_status(self, payload):
        """Handle status update with type parsing."""
        dp_code = payload["code"]
        value = payload["value"]

        try:
            if dp_code == self._dp["current_temperature_code"]:
                if self._current_temp_type == "float":
                    self._current_temp = float(value) / 10
                elif self._current_temp_type == "integer":
                    self._current_temp = int(value)
                else:
                    self._current_temp = value

            elif dp_code == self._dp["target_temperature_code"]:
                if self._target_temp_type == "float":
                    self._target_temp = float(value) / 10
                elif self._target_temp_type == "integer":
                    self._target_temp = int(value)
                else:
                    self._target_temp = value

            elif dp_code == self._dp["hvac_modes_code"]:
                if self._mode_type in ("enum", "string"):
                    self._mode_value = str(value)
                else:
                    self._mode_value = value

            elif self._has_switch and dp_code == self._dp["switch_code"]:
                if self._switch_type == "boolean":
                    self._switch_state = bool(value)
                else:
                    self._switch_state = value

            else:
                _LOGGER.warning("[%s] ⚠️ Unexpected climate payload: %s", DOMAIN, payload)

        except (TypeError, ValueError):
            _LOGGER.exception("[%s] ❌ Parsing error for climate payload: %s", DOMAIN, payload)

        _LOGGER.debug("[%s] ✅ Updated climate %s from %s: %s",
                      DOMAIN, self._attr_unique_id, dp_code, value)
        self.async_write_ha_state()

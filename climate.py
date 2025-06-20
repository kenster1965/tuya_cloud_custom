"""Tuya Cloud Custom - Climate platform."""

import logging
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
)
from homeassistant.components.climate.const import (
    HVACMode,
)
from .const import DOMAIN
from .helpers.helper import build_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom climates."""
    devices = hass.data[DOMAIN]["devices"]
    climates = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "climate" and dp.get("enabled", True):
                climates.append(TuyaCloudClimate(hass, device, dp))
    async_add_entities(climates)
    _LOGGER.info("[%s] ✅ Registered %s climates", DOMAIN, len(climates))


class TuyaCloudClimate(ClimateEntity):
    """Tuya Cloud Custom Climate."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
    )

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        # Required mappings
        self._unique_id = dp.get("unique_id")
        self._current_temp_code = dp["current_temperature_code"]
        self._target_temp_code = dp["target_temperature_code"]
        self._hvac_modes_code = dp["hvac_modes_code"]
        self._switch_code = dp.get("switch_code")  # optional

        self._hvac_mode_map = dp.get("hvac_modes", {})

        self._attr_unique_id = self._unique_id
        self._attr_has_entity_name = False
        self._attr_temperature_unit = dp.get("temperature_unit", "°F")
        self._attr_min_temp = dp.get("min_temp", 60)
        self._attr_max_temp = dp.get("max_temp", 90)
        self._attr_precision = dp.get("precision", 1.0)

        self._attr_hvac_modes = list(HVACMode)
        self._attr_hvac_mode = HVACMode.OFF

        self._attr_current_temperature = None
        self._attr_target_temperature = None

        self._switch_state = None  # for optional switch

        key = (device["tuya_device_id"], self._hvac_modes_code)
        hass.data[DOMAIN]["entities"][key] = self

        if self._switch_code:
            key = (device["tuya_device_id"], self._switch_code)
            hass.data[DOMAIN]["entities"][key] = self

        key = (device["tuya_device_id"], self._current_temp_code)
        hass.data[DOMAIN]["entities"][key] = self

        key = (device["tuya_device_id"], self._target_temp_code)
        hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered climate entity: %s", DOMAIN, self._unique_id)

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_hvac_mode(self, hvac_mode):
        tuya_value = None
        for ha_mode, tuya_mode in self._hvac_mode_map.items():
            if ha_mode == hvac_mode:
                tuya_value = tuya_mode
                break

        if tuya_value is None:
            _LOGGER.error("[%s] ❌ Unknown hvac mode: %s", DOMAIN, hvac_mode)
            return

        await self._send_tuya_command(self._hvac_modes_code, tuya_value)

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        await self._send_tuya_command(self._target_temp_code, temperature)

    async def _send_tuya_command(self, dp_code, value):
        from .helpers.token_refresh import send_tuya_command
        await send_tuya_command(self._hass, self._device["tuya_device_id"], dp_code, value)

    async def async_update_from_status(self, payload):
        """Handle status update payload dict."""
        code = payload["code"]
        value = payload["value"]

        if code == self._current_temp_code:
            self._attr_current_temperature = float(value)
        elif code == self._target_temp_code:
            self._attr_target_temperature = float(value)
        elif code == self._hvac_modes_code:
            self._attr_hvac_mode = next(
                (ha_mode for ha_mode, tuya_val in self._hvac_mode_map.items() if tuya_val == value),
                HVACMode.OFF
            )
        elif code == self._switch_code:
            self._switch_state = bool(value)
        else:
            _LOGGER.warning("[%s] ⚠️ Unexpected DP code for climate: %s", DOMAIN, code)

        self.async_write_ha_state()

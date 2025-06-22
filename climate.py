"""Tuya Cloud Custom - Bulletproof Climate platform."""

import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .helpers.helper import build_device_info
from .helpers.tuya_command import send_tuya_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = hass.data[DOMAIN]["devices"]
    climates = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "climate" and dp.get("enabled", True):
                climates.append(TuyaCloudClimate(hass, device, dp))
    async_add_entities(climates)
    _LOGGER.info("[%s] ✅ Registered %s climates", DOMAIN, len(climates))


class TuyaCloudClimate(ClimateEntity):
    """Robust Tuya Cloud Custom Climate."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        self._attr_unique_id = dp.get("unique_id")
        self._attr_has_entity_name = False

        # 🌡️ Temperature props
        self._temp_convert = dp.get("temp_convert")  # e.g. c_to_f or None

        self._has_target_temperature = "target_temperature" in dp
        if self._has_target_temperature:
            tt = dp["target_temperature"]
            self._attr_min_temp = tt.get("min_temp", 10)
            self._attr_max_temp = tt.get("max_temp", 35)
            self._attr_precision = tt.get("precision", 1)
            self._attr_target_temperature_step = self._attr_precision
            self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        else:
            self._attr_supported_features = 0

        self._attr_temperature_unit = (
            UnitOfTemperature.FAHRENHEIT if self._temp_convert == "c_to_f" else UnitOfTemperature.CELSIUS
        )

        self._switch = dp.get("on_off", None)

        self._current_temp = None
        self._target_temp = None

        hvac_mode_def = dp["hvac_mode"]
        self._hvac_code = hvac_mode_def["code"]
        self._ha_to_tuya = hvac_mode_def["modes"]
        self._tuya_to_ha = {v: k for k, v in self._ha_to_tuya.items()}

        self._attr_hvac_modes = ["off"] + list(self._ha_to_tuya.keys())

        self._mode_value = None
        self._switch_state = None

        tid = device["tuya_device_id"]
        hass.data[DOMAIN]["entities"][(tid, dp["current_temperature"]["code"])] = self
        if self._has_target_temperature:
            hass.data[DOMAIN]["entities"][(tid, dp["target_temperature"]["code"])] = self
        hass.data[DOMAIN]["entities"][(tid, self._hvac_code)] = self
        if self._switch:
            hass.data[DOMAIN]["entities"][(tid, self._switch["code"])] = self

        _LOGGER.debug("[%s] ✅ Registered robust climate: %s", DOMAIN, self._attr_unique_id)

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
        if self._switch and self._switch_state is False:
            return HVACMode.OFF
        return self._tuya_to_ha.get(self._mode_value, HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        """Set target temperature with correct unit conversion and scaling."""
        new_temp = kwargs.get("temperature")
        if new_temp is None:
            return

        if self._temp_convert == "c_to_f":
            celsius = (float(new_temp) - 32) * 5 / 9
        else:
            celsius = float(new_temp)

        # ✅ Multiply by 10 to match Tuya's required format (tenths of °C)
        value = int(celsius * 10)

        await self._hass.async_add_executor_job(
            send_tuya_command,
            self._hass,
            self._device["tuya_device_id"],
            self._dp["target_temperature"]["code"],
            value
        )

        self._target_temp = new_temp
        self.async_write_ha_state()


    async def async_set_hvac_mode(self, hvac_mode):
        tid = self._device["tuya_device_id"]

        if hvac_mode == HVACMode.OFF:
            if self._switch:
                await self._hass.async_add_executor_job(
                    send_tuya_command,
                    self._hass,
                    tid,
                    self._switch["code"],
                    False
                )
        else:
            if self._switch:
                await self._hass.async_add_executor_job(
                    send_tuya_command,
                    self._hass,
                    tid,
                    self._switch["code"],
                    True
                )
            tuya_mode = self._ha_to_tuya.get(hvac_mode)
            if tuya_mode:
                await self._hass.async_add_executor_job(
                    send_tuya_command,
                    self._hass,
                    tid,
                    self._hvac_code,
                    tuya_mode
                )

        self.async_write_ha_state()

    async def async_update(self):
        pass

    async def async_update_from_status(self, payload):
        dp_code = payload["code"]
        val = payload["value"]

        if dp_code == self._dp["current_temperature"]["code"]:
            raw = float(val) / 10
            if self._temp_convert == "c_to_f":
                self._current_temp = round(raw * 9/5 + 32, 1)
            else:
                self._current_temp = raw

        elif self._has_target_temperature and dp_code == self._dp["target_temperature"]["code"]:
            raw = float(val) / 10
            if self._temp_convert == "c_to_f":
                self._target_temp = round(raw * 9/5 + 32, 1)
            else:
                self._target_temp = raw

        elif dp_code == self._hvac_code:
            self._mode_value = val

        elif self._switch and dp_code == self._switch["code"]:
            self._switch_state = bool(val)

        _LOGGER.debug("[%s] ✅ Climate %s DP %s = %s",
                      DOMAIN, self._attr_unique_id, dp_code, val)
        self.async_write_ha_state()

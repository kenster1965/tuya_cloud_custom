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

        # Unique ID is user-defined in YAML
        self._attr_unique_id = dp.get("unique_id")
        self._attr_has_entity_name = False

        # Temp & HVAC states
        self._current_temp = None
        self._target_temp = None
        self._hvac_mode = HVACMode.OFF

        # Switch (optional)
        self._switch_state = None
        self._has_switch = bool(dp.get("switch_code"))

        # Supported HVAC modes
        self._modes_map = dp.get("hvac_modes", {})
        self._attr_hvac_modes = list(self._modes_map.keys())

        # Units & limits
        self._attr_temperature_unit = dp.get("temperature_unit", UnitOfTemperature.CELSIUS)
        self._attr_min_temp = dp.get("min_temp", 10.0)
        self._attr_max_temp = dp.get("max_temp", 35.0)
        self._attr_precision = dp.get("precision", 1.0)

        # Register both primary & related keys
        tid = device["tuya_device_id"]
        for code in [dp["current_temperature_code"], dp["target_temperature_code"],
                     dp["hvac_modes_code"], dp.get("switch_code")]:
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
        return self._hvac_mode

    async def async_set_temperature(self, **kwargs):
        """Handle target temp change."""
        new_temp = kwargs.get("temperature")
        if new_temp is None:
            return
        resp = await self._hass.async_add_executor_job(
            send_tuya_command,
            self._hass,
            self._device["tuya_device_id"],
            self._dp["target_temperature_code"],
            new_temp
        )
        if resp and resp.status_code == 200:
            self._target_temp = new_temp
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Handle mode change, uses switch + mode if needed."""
        mode_val = self._dp["hvac_modes"].get(hvac_mode)
        tid = self._device["tuya_device_id"]

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
        """No polling — status.py pushes updates."""
        pass

    async def async_update_from_status(self, payload):
        """Update called by Status manager."""
        dp_code = payload["code"]
        value = payload["value"]

        if dp_code == self._dp["current_temperature_code"]:
            self._current_temp = float(value)
        elif dp_code == self._dp["target_temperature_code"]:
            self._target_temp = float(value)
        elif dp_code == self._dp["hvac_modes_code"]:
            # Invert map: DP value → HA mode
            for ha_mode, dp_mode in self._modes_map.items():
                if dp_mode == value:
                    self._hvac_mode = ha_mode
                    break
        elif self._has_switch and dp_code == self._dp["switch_code"]:
            if not value:
                self._hvac_mode = HVACMode.OFF
        else:
            _LOGGER.warning("[%s] ⚠️ Unexpected climate payload: %s", DOMAIN, payload)

        _LOGGER.debug("[%s] ✅ Updated climate %s from %s: %s", DOMAIN, self._attr_unique_id, dp_code, value)
        self.async_write_ha_state()

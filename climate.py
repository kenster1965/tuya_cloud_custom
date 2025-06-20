"""Tuya Cloud Custom - Climate platform."""

import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature
)
from .const import DOMAIN
from .helpers.helper import sanitize, build_device_info

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

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        # Stable unique_id: tuya_id + "_climate_" + custom unique id
        tuya_id = device["tuya_device_id"]
        unique_part = sanitize(dp.get("unique_id", "unknown"))
        self._attr_unique_id = f"{tuya_id}_climate_{unique_part}"

        self._attr_has_entity_name = False  # Entity name controlled in UI

        # DPs for status/commands
        self._current_temp_code = dp["current_temperature_code"]
        self._target_temp_code = dp["target_temperature_code"]
        self._hvac_modes_code = dp["hvac_modes_code"]
        self._switch_code = dp.get("switch_code")

        # Temp unit, range, precision
        self._attr_temperature_unit = dp.get("temperature_unit", "°C")
        self._attr_min_temp = dp.get("min_temp", 10.0)
        self._attr_max_temp = dp.get("max_temp", 35.0)
        self._attr_precision = dp.get("precision", 1.0)

        # Supported HVAC modes mapping
        self._tuya_modes = dp.get("hvac_modes", {})
        self._hvac_modes = list(self._tuya_modes.keys())
        self._attr_supported_hvac_modes = self._hvac_modes

        # State vars
        self._current_temp = None
        self._target_temp = None
        self._hvac_mode = HVACMode.OFF
        self._is_on = True  # Assume on by default

        # Register entity for all relevant DPs
        self._register_dp(hass, tuya_id, self._current_temp_code)
        self._register_dp(hass, tuya_id, self._target_temp_code)
        self._register_dp(hass, tuya_id, self._hvac_modes_code)
        if self._switch_code:
            self._register_dp(hass, tuya_id, self._switch_code)

        _LOGGER.debug("[%s] ✅ Registered climate: %s", DOMAIN, self._attr_unique_id)

    def _register_dp(self, hass, tuya_id, code):
        """Helper to register this climate entity for a DP code."""
        key = (tuya_id, code)
        hass.data[DOMAIN]["entities"][key] = self

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_temperature(self, **kwargs):
        value = kwargs.get("temperature")
        if value is None:
            return

        await self._send_command(self._target_temp_code, value)
        self._target_temp = value
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode (and power if switch DP exists)."""
        tuya_mode = self._tuya_modes.get(hvac_mode)
        if not tuya_mode:
            _LOGGER.warning("[%s] ❌ Invalid HVAC mode: %s", DOMAIN, hvac_mode)
            return

        if self._switch_code:
            if hvac_mode == HVACMode.OFF:
                await self._send_command(self._switch_code, False)
            else:
                await self._send_command(self._switch_code, True)
                await self._send_command(self._hvac_modes_code, tuya_mode)
        else:
            await self._send_command(self._hvac_modes_code, tuya_mode)

        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def _send_command(self, code, value):
        """Send command using the same pattern as other entities."""
        secrets = self._hass.data[DOMAIN]["secrets"]
        token_file = self._hass.data[DOMAIN]["token_file"]
        base_url = secrets["base_url"]
        client_id = secrets["client_id"]
        client_secret = secrets["client_secret"]

        import json, uuid, time, hmac, hashlib

        with open(token_file, "r") as f:
            token_data = json.load(f)
        access_token = token_data["access_token"]

        device_id = self._device["tuya_device_id"]
        url_path = f"/v1.0/devices/{device_id}/commands"
        url = f"{base_url}{url_path}"

        payload = {"commands": [{"code": code, "value": value}]}

        t = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        content_str = json.dumps(payload)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        string_to_sign = f"POST\n{content_hash}\n\n{url_path}"
        sign_str = client_id + access_token + t + nonce + string_to_sign
        signature = hmac.new(client_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest().upper()

        headers = {
            "client_id": client_id,
            "access_token": access_token,
            "sign": signature,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "nonce": nonce,
            "Content-Type": "application/json",
        }

        def _do_post():
            import requests
            response = requests.post(url, headers=headers, json=payload)
            _LOGGER.debug("[%s] Climate command [%s=%s] response: %s", DOMAIN, code, value, response.text)
            if response.status_code != 200:
                _LOGGER.error("[%s] Climate command failed: %s | %s", DOMAIN, response.status_code, response.text)

        await self._hass.async_add_executor_job(_do_post)

    async def async_update_from_status(self, value):
        """Update called when *any* relevant DP updates."""
        # The status poller feeds individual DP values:
        # So for each DP key -> update the right attribute.
        if isinstance(value, dict):
            # Unexpected, safeguard
            _LOGGER.warning("[%s] Unexpected value format: %s", DOMAIN, value)
            return

        # Figure out which DP key triggered this
        key = self._hass.data[DOMAIN]["entities"].get((self._device["tuya_device_id"], self._current_temp_code))
        if key == self:
            self._current_temp = float(value)
        elif self._hass.data[DOMAIN]["entities"].get((self._device["tuya_device_id"], self._target_temp_code)) == self:
            self._target_temp = float(value)
        elif self._hass.data[DOMAIN]["entities"].get((self._device["tuya_device_id"], self._hvac_modes_code)) == self:
            self._hvac_mode = next((k for k, v in self._tuya_modes.items() if v == value), HVACMode.OFF)
        elif self._switch_code and self._hass.data[DOMAIN]["entities"].get((self._device["tuya_device_id"], self._switch_code)) == self:
            self._is_on = bool(value)

        _LOGGER.debug("[%s] ✅ Climate updated: Temp=%s Target=%s Mode=%s Switch=%s",
                      DOMAIN, self._current_temp, self._target_temp, self._hvac_mode, self._is_on)

        self.async_write_ha_state()

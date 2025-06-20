"""Tuya Cloud Custom - Climate platform."""

import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature
from .const import DOMAIN
from .helpers.helper import build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom climate devices."""
    devices = hass.data[DOMAIN]["devices"]
    climates = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "climate" and dp.get("enabled", True):
                climates.append(TuyaCloudClimate(hass, device, dp))
    async_add_entities(climates)
    _LOGGER.info("[%s] ✅ Registered %s climate entities", DOMAIN, len(climates))


class TuyaCloudClimate(ClimateEntity):
    """Representation of a Tuya Cloud Custom Climate."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        self._unique_id = f"{device['tuya_device_id']}_{dp['unique_id']}"
        self._attr_unique_id = self._unique_id
        self._attr_name = dp.get("unique_id")
        self._attr_has_entity_name = False  # you control the name

        self._attr_temperature_unit = dp.get("temperature_unit", "°F")
        self._attr_min_temp = dp.get("min_temp", 59.0)
        self._attr_max_temp = dp.get("max_temp", 104.0)
        self._attr_precision = dp.get("precision", 1.0)

        self._attr_hvac_modes = list(dp.get("hvac_modes", {}).keys())
        self._hvac_map = dp.get("hvac_modes", {})

        # Optional switch control
        self._switch_code = dp.get("switch_code")
        self._switch_dp = dp.get("switch_dp")

        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = self._attr_hvac_modes[0] if self._attr_hvac_modes else "off"

        # Register this entity for status updates
        for code in [dp.get("current_temperature_code"), dp.get("target_temperature_code"), dp.get("hvac_modes_code"), self._switch_code]:
            if code:
                key = (device["tuya_device_id"], code)
                hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug("[%s] ✅ Registered climate entity: %s", DOMAIN, self._unique_id)

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get("temperature")
        if temp is None:
            return

        _LOGGER.debug("[%s] 🔥 Setting target temp to %s", DOMAIN, temp)

        await self._send_tuya_command(
            self._dp.get("target_temperature_code"),
            temp
        )
        self._target_temperature = temp
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        tuya_value = self._hvac_map.get(hvac_mode)
        if not tuya_value:
            _LOGGER.warning("[%s] ⚠️ Unsupported HVAC mode: %s", DOMAIN, hvac_mode)
            return

        _LOGGER.debug("[%s] 🔁 Setting HVAC mode to %s (Tuya: %s)", DOMAIN, hvac_mode, tuya_value)

        await self._send_tuya_command(
            self._dp.get("hvac_modes_code"),
            tuya_value
        )
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

        # If a switch is defined, turn it on for any mode except "off"
        if self._switch_code:
            await self._send_tuya_command(
                self._switch_code,
                hvac_mode != "off"
            )

    async def _send_tuya_command(self, code, value):
        """Send command to Tuya Cloud."""
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
        content_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
        string_to_sign = f"POST\n{content_hash}\n\n{url_path}"
        sign_str = client_id + access_token + t + nonce + string_to_sign
        signature = hmac.new(client_secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256).hexdigest().upper()

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
            resp = requests.post(url, headers=headers, json=payload)
            _LOGGER.debug("[%s] Climate command response: %s", DOMAIN, resp.text)
            if resp.status_code != 200:
                _LOGGER.error("[%s] Climate command failed: %s | %s", DOMAIN, resp.status_code, resp.text)

        await self._hass.async_add_executor_job(_do_post)

    async def async_update_from_status(self, val):
        """Update from status: expects {'code': X, 'value': Y}."""
        code = val["code"]
        value = val["value"]

        if code == self._dp.get("current_temperature_code"):
            self._current_temperature = float(value)
        elif code == self._dp.get("target_temperature_code"):
            self._target_temperature = float(value)
        elif code == self._dp.get("hvac_modes_code"):
            # Reverse map Tuya value back to HA mode
            rev_map = {v: k for k, v in self._hvac_map.items()}
            self._hvac_mode = rev_map.get(value, "off")
        elif code == self._switch_code:
            if not value:
                self._hvac_mode = "off"

        _LOGGER.debug("[%s] ✅ Updated climate %s: %s = %s", DOMAIN, self._unique_id, code, value)
        self.async_write_ha_state()

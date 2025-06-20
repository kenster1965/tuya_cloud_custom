"""Tuya Cloud Custom - Switch platform."""

import logging
from homeassistant.components.switch import SwitchEntity
from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN

import requests

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches."""
    devices = hass.data[DOMAIN]["devices"]
    switches = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(hass, device, dp))
    async_add_entities(switches)
    _LOGGER.info("[%s] ✅ Registered %s switches", DOMAIN, len(switches))


class TuyaCloudSwitch(SwitchEntity):
    """Tuya Cloud Custom Switch."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = False

        attrs = build_entity_attrs(device, dp, "switch")
        self._attr_unique_id = attrs["unique_id"]
        self._attr_has_entity_name = False  # prevent Name → Entity ID binding

        if "entity_category" in attrs:
            self._attr_entity_category = attrs["entity_category"]

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self
        _LOGGER.debug("[%s] ✅ Registered switch entity: %s", DOMAIN, key)

    @property
    def is_on(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_turn_on(self, **kwargs):
        await self._send_tuya_command(True)

    async def async_turn_off(self, **kwargs):
        await self._send_tuya_command(False)

    async def _send_tuya_command(self, state: bool):
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

        payload = {"commands": [{"code": self._dp["code"], "value": state}]}

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
            response = requests.post(url, headers=headers, json=payload)
            _LOGGER.debug("[%s] Switch command response: %s", DOMAIN, response.text)
            if response.status_code == 200:
                self._state = state
                self._hass.add_job(self.async_write_ha_state)
            else:
                _LOGGER.error("[%s] Switch command failed: %s | %s", DOMAIN, response.status_code, response.text)

        await self._hass.async_add_executor_job(_do_post)

    async def async_update(self):
        """Polling fallback (not used)."""
        pass

    async def async_update_from_status(self, val):
        """Update switch from status."""
        self._state = bool(val)
        _LOGGER.debug("[%s] ✅ Updated %s: %s", DOMAIN, self._attr_unique_id, self._state)
        self.async_write_ha_state()

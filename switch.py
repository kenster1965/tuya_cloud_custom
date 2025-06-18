import logging
import requests
import json
import time
import uuid
import hmac
import hashlib

from homeassistant.components.switch import SwitchEntity
from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom switches."""
    devices = hass.data[DOMAIN]["devices"]
    switches = []

    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "switch" and dp.get("enabled", True):
                switches.append(TuyaCloudSwitch(hass, device, dp))

    async_add_entities(switches)


class TuyaCloudSwitch(SwitchEntity):
    """Custom Tuya Cloud Switch."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        attrs = build_entity_attrs(device, dp, "switch", logger=_LOGGER)
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._tuya_device_id = device["tuya_device_id"]
        self._tuya_code = dp["code"]

        self._state = False

        key = (self._tuya_device_id, self._tuya_code)
        _LOGGER.debug(f"[{DOMAIN}] Registering switch entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

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

    async def _send_tuya_command(self, value: bool):
        """Send on/off command safely with proper token + thread safety."""
        secrets = self._hass.data[DOMAIN]["secrets"]
        token_file = self._hass.data[DOMAIN]["token_file"]

        client_id = secrets["client_id"]
        client_secret = secrets["client_secret"]
        base_url = secrets["base_url"]

        def _do_post():
            try:
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                access_token = token_data["access_token"]
            except Exception as e:
                _LOGGER.error(f"[{DOMAIN}] ❌ Failed to read token: {e}")
                return

            payload = {
                "commands": [
                    {"code": self._tuya_code, "value": value}
                ]
            }

            url_path = f"/v1.0/devices/{self._tuya_device_id}/commands"
            method = "POST"
            t = str(int(time.time() * 1000))
            nonce = str(uuid.uuid4())
            payload_str = json.dumps(payload)
            content_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
            sign_str = client_id + access_token + t + nonce + string_to_sign
            signature = hmac.new(
                client_secret.encode(),
                sign_str.encode(),
                hashlib.sha256
            ).hexdigest().upper()

            headers = {
                "client_id": client_id,
                "access_token": access_token,
                "sign": signature,
                "t": t,
                "sign_method": "HMAC-SHA256",
                "nonce": nonce,
                "Content-Type": "application/json",
            }

            url = f"{base_url}{url_path}"

            response = requests.post(url, headers=headers, data=payload_str)
            _LOGGER.debug(f"[{DOMAIN}] 📡 Switch command response: {response.status_code} | {response.text}")

            if response.status_code == 200 and response.json().get("success"):
                self._state = value
                self._hass.add_job(self.async_write_ha_state)
                _LOGGER.info(f"[{DOMAIN}] ✅ Switch command successful.")
            else:
                _LOGGER.error(f"[{DOMAIN}] ❌ Switch command failed: {response.status_code} | {response.text}")

        await self._hass.async_add_executor_job(_do_post)

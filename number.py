import logging
import requests
import json
import time
import uuid
import hmac
import hashlib

from homeassistant.components.number import NumberEntity
from .helpers.helper import build_entity_attrs, build_device_info
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom numbers."""
    devices = hass.data[DOMAIN]["devices"]
    numbers = []

    for device in devices:
        for dp in device.get("dps", []):
            if dp.get("platform") == "number" and dp.get("enabled", True):
                numbers.append(TuyaCloudNumber(hass, device, dp))

    async_add_entities(numbers)


class TuyaCloudNumber(NumberEntity):
    """Custom Tuya Cloud Number."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp

        attrs = build_entity_attrs(device, dp, "number", logger=_LOGGER)

        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]

        self._attr_native_min_value = attrs.get("min", 0.0)
        self._attr_native_max_value = attrs.get("max", 100.0)
        self._attr_native_step = attrs.get("step", 1.0)

        self._tuya_device_id = device["tuya_device_id"]
        self._tuya_code = dp["code"]

        # Safe initial value to avoid "unavailable"
        default = dp.get("dps_default_value", self._attr_native_min_value)
        self._value = float(default)

        key = (self._tuya_device_id, self._tuya_code)
        _LOGGER.debug(f"[{DOMAIN}] Registering number entity: {key}")
        self._hass.data[DOMAIN]["entities"][key] = self

    @property
    def native_value(self):
        return self._value

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_set_native_value(self, value: float):
        await self._send_tuya_command(value)

    async def _send_tuya_command(self, value: float):
        """Safe: open token + post in executor."""
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

            # 🔑 Ensure correct type: int if step is 1
            send_value = int(value) if self._attr_native_step == 1.0 else value

            payload = {
                "commands": [
                    {"code": self._tuya_code, "value": send_value}
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
            _LOGGER.debug(f"[{DOMAIN}] 📡 Number command response: {response.status_code} | {response.text}")

            if response.status_code == 200 and response.json().get("success"):
                self._value = send_value
                self._hass.add_job(self.async_write_ha_state)
                _LOGGER.info(f"[{DOMAIN}] ✅ Number command successful.")
            else:
                _LOGGER.error(f"[{DOMAIN}] ❌ Number command failed: {response.status_code} | {response.text}")

        await self._hass.async_add_executor_job(_do_post)

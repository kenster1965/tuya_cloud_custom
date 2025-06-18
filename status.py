"""
Tuya Cloud Custom: Status Poller
--------------------------------
Polls Tuya Cloud API safely.
Uses executor for blocking HTTP. Schedules polling on loop only.
"""

import json
import time
import uuid
import hmac
import hashlib
import logging
import requests

from datetime import timedelta

from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .helpers.device_loader import load_tuya_devices

_LOGGER = logging.getLogger(__name__)


class Status:
    """Polls Tuya Cloud API for device status."""

    def __init__(self, hass):
        self.hass = hass
        self.devices_file = hass.data[DOMAIN]["devices_file"]
        self.token_file = hass.data[DOMAIN]["token_file"]
        self.secrets = hass.data[DOMAIN]["secrets"]

        self.client_id = self.secrets["client_id"]
        self.client_secret = self.secrets["client_secret"]
        self.base_url = self.secrets["base_url"]

    async def async_start_polling(self):
        """Load devices + schedule safe polling."""
        _LOGGER.info(f"[{DOMAIN}] 🚦 async_start_polling called...")

        self.devices = await self.hass.async_add_executor_job(
            load_tuya_devices, self.devices_file
        )
        _LOGGER.info(f"[{DOMAIN}] 🚦 Loaded {len(self.devices)} devices to poll.")

        if not self.devices:
            _LOGGER.warning(f"[{DOMAIN}] ⚠️ No devices found — skipping polling.")
            return

        for device in self.devices:
            if not device.get("enabled", True):
                _LOGGER.info(f"[{DOMAIN}] ⏹️ '{device.get('ha_name')}' disabled.")
                continue

            interval_sec = device.get("poll_interval")
            if not isinstance(interval_sec, (int, float)) or interval_sec <= 0:
                interval_sec = 3600
                _LOGGER.warning(
                    f"[{DOMAIN}] ⚠️ Invalid 'poll_interval' for '{device.get('ha_name')}', using default {interval_sec}s."
                )

            _LOGGER.info(
                f"[{DOMAIN}] ⏱️ Polling every {interval_sec} sec for '{device.get('ha_name')}'"
            )

            async_track_time_interval(
                self.hass,
                self._make_async_poll_callback(device),
                timedelta(seconds=interval_sec)
            )

    def _make_async_poll_callback(self, device):
        async def _poll(now):
            await self.async_fetch_status(device)
        return _poll

    async def async_fetch_status(self, device):
        """Poll status — blocking work runs off loop."""
        ha_name = device.get("ha_name")

        try:
            response = await self.hass.async_add_executor_job(
                self._fetch_status_sync, device
            )
            if response is None:
                _LOGGER.warning(f"[{DOMAIN}] ⚠️ No response for {ha_name}.")
                return

            if response.status_code == 200 and response.json().get("success"):
                status_data = response.json().get("result", [])
                _LOGGER.info(f"[{DOMAIN}] ✅ Status for {ha_name}: {status_data}")

                device_id = device.get("tuya_device_id")
                entities = self.hass.data.get(DOMAIN, {}).get("entities")
                if not entities:
                    _LOGGER.warning(f"[{DOMAIN}] ⚠️ No entities dict found — skipping update for {ha_name}.")
                    return

                for dp in status_data:
                    code = dp["code"]
                    value = dp["value"]
                    key = (device_id, code)
                    entity = entities.get(key)
                    if entity:
                        entity._state = value
                        entity.async_write_ha_state()
                        _LOGGER.debug(f"[{DOMAIN}] 🔄 Updated {key} = {value}")
                    else:
                        _LOGGER.debug(f"[{DOMAIN}] ⚠️ No entity registered for {key}")

            else:
                _LOGGER.error(f"[{DOMAIN}] ❌ API error for {ha_name}: {response.json()}")

        except Exception as e:
            _LOGGER.exception(f"[{DOMAIN}] 💥 Exception fetching status for {ha_name}: {e}")

    def _fetch_status_sync(self, device):
        """Do blocking HTTP GET off loop."""
        ha_name = device.get("ha_name")
        device_id = device.get("tuya_device_id")

        try:
            with open(self.token_file, "r") as f:
                token_data = json.load(f)
            access_token = token_data["access_token"]
        except Exception as e:
            _LOGGER.error(f"[{DOMAIN}] ❌ Token read failed: {e}")
            return None

        url_path = f"/v1.0/devices/{device_id}/status"
        method = "GET"

        t = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        content_hash = hashlib.sha256(b"").hexdigest()
        string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
        sign_str = self.client_id + access_token + t + nonce + string_to_sign

        signature = hmac.new(
            self.client_secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest().upper()

        headers = {
            "client_id": self.client_id,
            "access_token": access_token,
            "sign": signature,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "nonce": nonce,
        }

        url = f"{self.base_url}{url_path}"
        response = requests.get(url, headers=headers)
        return response

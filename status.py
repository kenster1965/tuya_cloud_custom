import asyncio
import logging
import json
import time
import uuid
import hmac
import hashlib

from datetime import timedelta

from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import HomeAssistant

from .const import DOMAIN

import requests  # ✅ Called safely in executor

_LOGGER = logging.getLogger(__name__)

class Status:
    """Tuya Cloud Custom: Periodic Status Poller."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.devices = hass.data[DOMAIN]["devices"]
        self.secrets = hass.data[DOMAIN]["secrets"]

        self.base_url = self.secrets["base_url"]
        self.client_id = self.secrets["client_id"]
        self.client_secret = self.secrets["client_secret"]
        self.token_file = hass.data[DOMAIN]["token_file"]

    async def async_start_polling(self):
        """Kick off periodic polling for each device."""
        for device in self.devices:
            if not device.get("enabled", True):
                _LOGGER.info("[%s] ⏹️ Device %s is disabled; skipping.", DOMAIN, device.get("tuya_device_id"))
                continue

            interval = device.get("poll_interval", 3600)
            try:
                interval = int(interval)
            except ValueError:
                interval = 3600

            if interval <= 0:
                interval = 3600

            _LOGGER.info("[%s] ⏱️ Scheduling status every %s sec for %s",
                        DOMAIN, interval, device.get("tuya_device_id"))

            async def _poll_device(now, dev=device):
                await self.async_fetch_status(dev)

            async_track_time_interval(
                self.hass,
                _poll_device,
                timedelta(seconds=interval)
            )


    async def async_fetch_status(self, device: dict):
        """Fetch status for one device, safely in executor."""

        def _do_request():
            try:
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                access_token = token_data["access_token"]

                device_id = device["tuya_device_id"]
                method = "GET"
                url_path = f"/v1.0/devices/{device_id}/status"
                t = str(int(time.time() * 1000))
                nonce = str(uuid.uuid4())
                content_hash = hashlib.sha256("".encode()).hexdigest()
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
                    "nonce": nonce
                }

                url = f"{self.base_url}{url_path}"
                response = requests.get(url, headers=headers, timeout=10)
                return response
            except Exception as e:
                _LOGGER.exception("[%s] ❌ Exception in status request: %s", DOMAIN, e)
                return None

        response = await self.hass.async_add_executor_job(_do_request)

        if response and response.status_code == 200 and response.json().get("success"):
            payload = response.json()["result"]
            for dp in payload:
                dp_code = dp["code"]
                value = dp["value"]
                key = (device["tuya_device_id"], dp_code)
                entity = self.hass.data[DOMAIN]["entities"].get(key)
                if entity:
                    await entity.async_update_from_status(value)
                else:
                    _LOGGER.debug("[%s] ⚠️ No entity found for %s (DP: %s)", DOMAIN, key, dp_code)
        else:
            _LOGGER.error("[%s] ❌ API error for %s: %s",
                DOMAIN, device.get("tuya_device_id"), response.text if response else "No response")

    async def async_fetch_all_devices(self):
        """Manually force-refresh all devices at once (e.g., after token refresh)."""
        tasks = [self.async_fetch_status(device) for device in self.devices if device.get("enabled", True)]
        await asyncio.gather(*tasks)

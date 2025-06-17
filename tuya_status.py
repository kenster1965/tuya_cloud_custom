import asyncio
import json
import hmac
import hashlib
import uuid
import time
import yaml
import aiohttp
import os

import logging
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TuyaStatus:
    """Handles polling Tuya Cloud device status."""

    def __init__(self, hass):
        self.hass = hass

        # ✅ Use paths & secrets from hass.data
        self.token_file = hass.data[DOMAIN]["token_file"]
        self.devices_file = hass.data[DOMAIN]["devices_file"]

        secrets = hass.data[DOMAIN].get("secrets", {})
        self.client_id = secrets.get("client_id")
        self.client_secret = secrets.get("client_secret")
        self.base_url = secrets.get("base_url")

        # Load devices from YAML
        try:
            with open(self.devices_file, "r") as f:
                self.devices = yaml.safe_load(f).get("devices", [])
        except Exception as e:
            _LOGGER.error(f"[{DOMAIN}] ❌ Failed to load devices: {e}")
            self.devices = []

    async def async_start_polling(self):
        """Schedule periodic status checks per device."""

        for device in self.devices:
            if not device.get("enabled", True):
                _LOGGER.info(f"[{DOMAIN}] ⏹️ Device '{device.get('ha_name')}' disabled — skipping.")
                continue

            # Validate poll_interval in SECONDS
            interval_sec = device.get("poll_interval")
            if isinstance(interval_sec, (int, float)) and interval_sec > 0:
                interval_sec = int(interval_sec)
            else:
                interval_sec = 3600  # default to 60 minutes
                _LOGGER.warning(
                    f"[{DOMAIN}] ⚠️ 'poll_interval' missing or invalid for "
                    f"device '{device.get('ha_name')}'. Using default {interval_sec} sec (60 min)."
                )

            _LOGGER.info(
                f"[{DOMAIN}] ⏱️ Scheduling status every {interval_sec} sec for '{device.get('ha_name')}'"
            )

            async_track_time_interval(
                self.hass,
                lambda now, dev=device: self.hass.async_create_task(
                    self.async_fetch_status(dev)
                ),
                timedelta(seconds=interval_sec)
            )

    async def async_fetch_status(self, device):
        """Fetch status for a single device from Tuya Cloud."""
        try:
            if not os.path.exists(self.token_file):
                _LOGGER.error(f"[{DOMAIN}] ❌ Token file missing: {self.token_file}")
                return

            with open(self.token_file, "r") as f:
                token_data = json.load(f)

            access_token = token_data.get("access_token")
            device_id = device.get("tuya_device_id")
            ha_name = device.get("ha_name", "unnamed")

            if not device_id:
                _LOGGER.error(f"[{DOMAIN}] ❌ Device '{ha_name}' missing tuya_device_id")
                return

            # Build signed request
            method = "GET"
            url_path = f"/v1.0/devices/{device_id}/status"
            url = f"{self.base_url.rstrip('/')}{url_path}"
            t = str(int(time.time() * 1000))
            nonce = str(uuid.uuid4())
            content_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
            string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
            sign_str = f"{self.client_id}{access_token}{t}{nonce}{string_to_sign}"

            signature = hmac.new(
                self.client_secret.encode("utf-8"),
                sign_str.encode("utf-8"),
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

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _LOGGER.info(f"[{DOMAIN}] ✅ Status for '{ha_name}': {data}")
                        # TODO: update entity states here
                    else:
                        text = await resp.text()
                        _LOGGER.error(f"[{DOMAIN}] ❌ Status failed for '{ha_name}': {resp.status} - {text}")

        except Exception as e:
            _LOGGER.exception(f"[{DOMAIN}] 💥 Exception fetching status for '{device.get('ha_name', 'unknown')}': {e}")

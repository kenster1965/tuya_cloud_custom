import logging
import time
import uuid
import json
import hmac
import hashlib
import yaml

from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN
from .helpers.device_loader import load_tuya_devices

_LOGGER = logging.getLogger(__name__)


class Status:
    """Central Tuya Cloud status poller."""

    def __init__(self, hass):
        self.hass = hass

        # ✅ Runtime config
        self.token_file = hass.data[DOMAIN]["token_file"]
        self.devices_file = hass.data[DOMAIN]["devices_file"]

        secrets = hass.data[DOMAIN]["secrets"]
        self.client_id = secrets.get("client_id")
        self.client_secret = secrets.get("client_secret")
        self.base_url = secrets.get("base_url")

        self.devices = []  # ✅ Will be loaded async later

    async def async_start_polling(self):
        """Load devices + schedule periodic status checks per device."""

        # ✅ Load devices YAML safely off the event loop
        self.devices = await self.hass.async_add_executor_job(
            load_tuya_devices, self.devices_file
        )

        if not self.devices:
            _LOGGER.warning(f"[{DOMAIN}] ⚠️ No devices found in {self.devices_file} — nothing to poll.")
            return

        for device in self.devices:
            if not device.get("enabled", True):
                _LOGGER.info(f"[{DOMAIN}] ⏹️ Device '{device.get('ha_name')}' disabled — skipping.")
                continue

            # Validate poll_interval in SECONDS
            interval_sec = device.get("poll_interval")
            if isinstance(interval_sec, (int, float)) and interval_sec > 0:
                interval_sec = int(interval_sec)
            else:
                interval_sec = 3600  # default to 60 min
                _LOGGER.warning(
                    f"[{DOMAIN}] ⚠️ 'poll_interval' missing or invalid for "
                    f"device '{device.get('ha_name')}'. Using default {interval_sec} sec."
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
        """Call Tuya Cloud API for a single device's status and update entities."""

        try:
            # Load token off-thread
            token_data = await self.hass.async_add_executor_job(self._load_token)
            access_token = token_data.get("access_token")
            if not access_token:
                _LOGGER.error(f"[{DOMAIN}] ❌ Missing access_token in token file.")
                return

            device_id = device.get("tuya_device_id")
            ha_name = device.get("ha_name", "unnamed_device")

            if not device_id:
                _LOGGER.error(f"[{DOMAIN}] ⚠️ Missing tuya_device_id for {ha_name}")
                return

            # 🔐 Build request signature
            method = "GET"
            url_path = f"/v1.0/devices/{device_id}/status"
            url = f"{self.base_url}{url_path}"
            t = str(int(time.time() * 1000))
            nonce = str(uuid.uuid4())
            content_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
            string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
            sign_str = self.client_id + access_token + t + nonce + string_to_sign

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
                "nonce": nonce
            }

            # 🌐 Send request in executor to keep loop free
            import requests
            response = await self.hass.async_add_executor_job(
                requests.get, url, {"headers": headers}
            )

            if response.status_code != 200:
                _LOGGER.error(
                    f"[{DOMAIN}] ❌ Status request failed for {ha_name}: "
                    f"{response.status_code} — {response.text}"
                )
                return

            data = response.json()
            if not data.get("success"):
                _LOGGER.error(
                    f"[{DOMAIN}] ❌ API error for {ha_name}: {data}"
                )
                return

            _LOGGER.debug(f"[{DOMAIN}] ✅ Status for {ha_name}: {json.dumps(data, indent=2)}")

            result = data.get("result", [])
            for dp in result:
                dp_code = dp.get("code")
                value = dp.get("value")
                key = (device_id, dp_code)

                entity = self.hass.data[DOMAIN]["entities"].get(key)
                if entity:
                    # Switch uses bool, Number uses float, Sensor is pass-through
                    if hasattr(entity, "_state"):
                        entity._state = value
                    elif hasattr(entity, "_value"):
                        entity._value = value
                    entity.async_write_ha_state()
                    _LOGGER.debug(f"[{DOMAIN}] Updated {key} = {value}")
                else:
                    _LOGGER.debug(f"[{DOMAIN}] No matching entity for {key}")

        except Exception as e:
            _LOGGER.exception(f"[{DOMAIN}] 💥 Exception fetching status: {e}")

    def _load_token(self):
        """Blocking helper to read token JSON file safely."""
        with open(self.token_file, "r") as f:
            return json.load(f)

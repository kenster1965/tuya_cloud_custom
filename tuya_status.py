import appdaemon.plugins.hass.hassapi as hass
import requests
import time
from datetime import timedelta
import uuid
import json
import hmac
import hashlib
import yaml

class TuyaStatus(hass.Hass):
    def initialize(self):
        self.log("📡 TuyaStatus initializing...")

        self.client_id = self.args["client_id"]
        self.client_secret = self.args["client_secret"]

        device_path = self.args.get("device_path", "/share/tuya_devices.yaml")

        try:
            with open(device_path, "r") as f:
                self.devices = yaml.safe_load(f).get("devices", [])
        except Exception as e:
            self.log(f"❌ Failed to load devices config: {e}", level="ERROR")
            self.devices = []

        for device in self.devices:
            if not device.get("enabled", True):
                self.log(f"⏹️ Device '{device.get('friendly_name')}' is disabled, skipping.")
                continue

            interval = device.get("poll_interval")
            if interval:
                self.log(f"⏱️ Scheduling '{device['friendly_name']}' every {interval} seconds")
                self.run_every(self.fetch_status, self.datetime() + timedelta(seconds=5), interval, device=device)
            else:
                self.log(f"⚠️ No poll_interval found for device '{device.get('friendly_name', 'unknown')}', skipping...")

    def fetch_status(self, kwargs):
        device = kwargs["device"]
        try:
            with open("/share/tuya_token.json", "r") as f:
                token_data = json.load(f)

            access_token = token_data["access_token"]

            # 🔁 Always use tuya_device_id for API calls
            device_id = device.get("tuya_device_id")
            ha_name = device.get("ha_name", "unnamed_device")
            friendly_name = device.get("friendly_name", ha_name)

            if not device_id:
                self.log(f"⚠️ Missing tuya_device_id in device: {friendly_name}", level="ERROR")
                return

            # 🔐 Build Tuya API signature
            method = "GET"
            url_path = f"/v1.0/devices/{device_id}/status"
            url = f"https://openapi.tuyaus.com{url_path}"
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

            # 🌐 Send request
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                status_data = response.json()
                #self.log(f"✅ Status for {friendly_name}:\n{json.dumps(status_data, indent=2)}")
                self.log(f"✅ Status for {friendly_name}")
            else:
                self.log(f"❌ Failed to get status for {friendly_name}: {response.status_code} - {response.text}")

        except Exception as e:
            self.log(f"💥 Exception checking status of '{device.get('friendly_name', 'unknown')}': {e}", level="ERROR")

"""
Kenster1965's Tuya Token Refresh AppDaemon App
Tuya Token Refresh AppDaemon App
This app refreshes the Tuya API token periodically and saves it to a JSON file.
It also handles the case where the refresh token is invalid or expired by 
requesting a new token or if file is not there.
It reads the client_id and client_secret from secrets.yaml.
"""

import appdaemon.plugins.hass.hassapi as hass
import yaml
import requests
import time
from datetime import timedelta
import json
import hmac
import hashlib
import uuid
# import os


class TuyaTokenRefresh(hass.Hass):
    """
    AppDaemon app to refresh Tuya API tokens periodically.
    This app reads client_id and client_secret from secrets.yaml,
    refreshes the token using the refresh_token, and saves the new token
    to a JSON file at /share/tuya_token.json.
    If the refresh fails, it attempts to get a new token using the client_id
    and client_secret.
    """

    # Initialize the app
    # This method is called when the app is started
    def initialize(self):
        self.log("🔄 Starting Tuya token refresh...")
        #self.log(f"tuya token ARGS: {self.args}")
        self.token_path = self.args.get("token_path", "/share/tuya_token.json")
        self.base_url = "https://openapi.tuyaus.com"

        self.log("🔐 Loading secrets.yaml")
        secrets_file = "/config/secrets.yaml"
        try:
            with open(secrets_file, "r") as f:
                secrets = yaml.safe_load(f)
                self.client_id = secrets.get("client_id")
                self.client_secret = secrets.get("client_secret")
        except Exception as e:
            self.log(f"💥 Failed to load secrets.yaml: {e}")
            return
        if not self.client_id or not self.client_secret:
            self.log("❌ Missing client_id or client_secret in secrets.yaml")
            return
        else:
            self.log("🔑 Loaded client_id and client_secret from secrets.yaml")
            self.refresh_token()
        # Schedule the token refresh every 90 minutes
        self.run_every(self.refresh_token, self.datetime() + timedelta(minutes=90), 5400)


    # Method to refresh the token using the refresh_token
    # It reads the client_id and client_secret from secrets.yaml,
    # then makes an API call to refresh the token.
    def refresh_token(self):
        # Load current refresh_token
        try:
            with open(self.token_path, "r") as f:
                current_token = json.load(f)
                refresh_token = current_token.get("refresh_token")
        except FileNotFoundError:
            self.log("📂 tuya_token.json not found. Requesting new token instead...")
            self.get_new_token()
            return  # ✅ Exit so we don't continue refresh
        except Exception as e:
            self.log(f"💥 Failed to read existing token file: {e}")
            self.get_new_token()
            return

        if not refresh_token:
            self.log("❌ No refresh_token found in the token file. Requesting new token...")
            self.get_new_token()
            return

        # Prepare API call to refresh token
        url_path = f"/v1.0/token/{refresh_token}"
        method = "GET"
        t = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        content_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
        string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
        sign_str = self.client_id + t + nonce + string_to_sign

        signature = hmac.new(
            self.client_secret.encode("utf-8"),
            msg=sign_str.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest().upper()

        headers = {
            "client_id": self.client_id,
            "sign": signature,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "nonce": nonce,
            "Content-Type": "application/json",
        }
        url = self.base_url + url_path

        try:
            self.log("🔁 Requesting new token using refresh_token...")
            response = requests.get(url, headers=headers)
            self.log(f"🌐 Tuya Status: {response.status_code}")
            self.log(f"📦 Tuya Response: {response.text}")

            if response.status_code == 200 and response.json().get("success"):
                result = response.json()["result"]
                with open(self.token_path, "w") as f:
                    json.dump(result, f, indent=2)
                self.log("✅ Token refreshed and saved successfully.")
                return  # ✅ EXIT so fallback doesn't run
            else:
                self.log(f"❌ Failed to refresh token: {response.text}")
        except Exception as e:
            self.log(f"💥 Exception during token refresh: {e}")

        # Fallback: get a new token
        self.log("🔄 Fallback: Requesting new token from Tuya API...")
        self.get_new_token()


    # Fallback method to get a new token if refresh fails
    # This is used when the refresh_token is invalid or expired
    def get_new_token(self):
        self.log("🔄 Getting NEW token from Tuya...")
        url_path = "/v1.0/token?grant_type=1"
        method = "GET"

        # with timestamp build the headers, signature, and URL
        t = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        content_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
        string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
        sign_str = self.client_id + t + nonce + string_to_sign
        signature = hmac.new(
            self.client_secret.encode("utf-8"),
            msg=sign_str.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest().upper()

        headers = {
            "client_id": self.client_id,
            "sign": signature,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "nonce": nonce,
            "Content-Type": "application/json",
        }

        # Request
        try:
            self.log("📡 Sending request for new token to Tuya...")
            response = requests.get(self.base_url + url_path, headers=headers)
            self.log(f"🌐 Tuya Status: {response.status_code}")
            self.log(f"📦 Tuya Response: {response.text}")

            # Save access_token to JSON file if successful
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    with open(self.token_path, "w") as f:
                        json.dump(data["result"], f, indent=2)
                    self.log("✅ New token fetched and saved successfully.")
                else:
                    self.log(f"❌ Error fetching new token: {response.status_code} - {response.text}")
            else:
                self.log(f"❌ Error fetching token: {response.status_code} - {response.text}")    
        except Exception as e:
            self.log(f"💥 Exception while getting new token: {e}")

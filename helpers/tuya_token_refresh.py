"""
Kenster1965's Tuya Token Refresh Helper
-------------------------------------------------
This standalone helper refreshes the Tuya Cloud API token
and saves it to a JSON file, using credentials and base_url
from secrets.yaml.

It works both:
✅ As a helper called by your custom HA integration
✅ Standalone if run manually (for testing or cron)
"""

import os
import yaml
import requests
import time
from datetime import timedelta
import json
import hmac
import hashlib
import uuid

# ------------------------------------------------------------------------------
# 📁 Dynamic paths: always resolved relative to this file
# ------------------------------------------------------------------------------

HERE = os.path.dirname(__file__)
PARENT = os.path.abspath(os.path.join(HERE, ".."))

CONFIG_PATH = os.path.join(PARENT, "config")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

# ------------------------------------------------------------------------------
# 🪵 Simple logger: works standalone & in HA logs if wrapped
# ------------------------------------------------------------------------------

def log(msg):
    print(f"[TuyaTokenRefresh] {msg}")

# ------------------------------------------------------------------------------
# 🔑 Load secrets.yaml
# ------------------------------------------------------------------------------

def load_secrets():
    """
    Load client_id, client_secret, and base_url from secrets.yaml
    """
    try:
        with open(SECRETS_FILE, "r") as f:
            secrets = yaml.safe_load(f)
        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")
        if not client_id or not client_secret or not base_url:
            raise ValueError("Missing client_id, client_secret, or base_url in secrets.yaml")
        return client_id, client_secret, base_url
    except Exception as e:
        log(f"💥 Failed to load secrets.yaml: {e}")
        raise

# ------------------------------------------------------------------------------
# 🔄 Refresh token using existing refresh_token
# ------------------------------------------------------------------------------

def refresh_token():
    """Refresh the Tuya token if possible; fallback to new token if needed."""
    client_id, client_secret, base_url = load_secrets()

    try:
        with open(TOKEN_FILE, "r") as f:
            current_token = json.load(f)
            refresh_token = current_token.get("refresh_token")
    except FileNotFoundError:
        log("📂 tuya_token.json not found. Requesting new token instead...")
        return get_new_token()
    except Exception as e:
        log(f"💥 Failed to read token file: {e}")
        return get_new_token()

    if not refresh_token:
        log("❌ No refresh_token found. Requesting new token instead...")
        return get_new_token()

    url_path = f"/v1.0/token/{refresh_token}"
    method = "GET"
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    content_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
    string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
    sign_str = client_id + t + nonce + string_to_sign

    signature = hmac.new(
        client_secret.encode("utf-8"),
        msg=sign_str.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": client_id,
        "sign": signature,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
        "Content-Type": "application/json",
    }

    url = base_url + url_path

    try:
        log("🔁 Requesting refreshed token...")
        response = requests.get(url, headers=headers)
        log(f"🌐 Status: {response.status_code}")
        log(f"📦 Response: {response.text}")

        if response.status_code == 200 and response.json().get("success"):
            result = response.json()["result"]
            with open(TOKEN_FILE, "w") as f:
                json.dump(result, f, indent=2)
            log("✅ Token refreshed and saved successfully.")
            return result
        else:
            log(f"❌ Failed to refresh: {response.text}")
    except Exception as e:
        log(f"💥 Exception during refresh: {e}")

    log("🔄 Fallback: requesting new token instead...")
    return get_new_token()

# ------------------------------------------------------------------------------
# 🆕 Fallback: request a new token from scratch
# ------------------------------------------------------------------------------

def get_new_token():
    """Request a completely new token using client_id and client_secret"""
    client_id, client_secret, base_url = load_secrets()
    url_path = "/v1.0/token?grant_type=1"
    method = "GET"

    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    content_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
    string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
    sign_str = client_id + t + nonce + string_to_sign

    signature = hmac.new(
        client_secret.encode("utf-8"),
        msg=sign_str.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": client_id,
        "sign": signature,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
        "Content-Type": "application/json",
    }

    try:
        log("📡 Requesting NEW token from Tuya...")
        response = requests.get(base_url + url_path, headers=headers)
        log(f"🌐 Status: {response.status_code}")
        log(f"📦 Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                with open(TOKEN_FILE, "w") as f:
                    json.dump(data["result"], f, indent=2)
                log("✅ New token fetched and saved successfully.")
                return data["result"]
            else:
                log(f"❌ Error fetching new token: {data}")
        else:
            log(f"❌ HTTP error: {response.status_code}")
    except Exception as e:
        log(f"💥 Exception while requesting new token: {e}")

    return None

# ------------------------------------------------------------------------------
# 🏃 Run standalone (optional)
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    refresh_token()

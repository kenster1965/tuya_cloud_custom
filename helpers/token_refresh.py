"""
Tuya Cloud Custom: Token Refresh Helper
---------------------------------------
Handles requesting or refreshing the Tuya Cloud access token.
"""

import json
import time
import uuid
import yaml
import hmac
import hashlib
import logging
import requests  # only runs in executor

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

def refresh_token(secrets_file, token_file):
    """Refresh or request a new Tuya Cloud API token."""

    try:
        with open(secrets_file, "r") as f:
            secrets = yaml.safe_load(f)

        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")

        if not client_id or not client_secret or not base_url:
            _LOGGER.error(f"[{DOMAIN}] ❌ secrets.yaml missing fields.")
            return

        try:
            with open(token_file, "r") as f:
                current_token = json.load(f)
                refresh_token_val = current_token.get("refresh_token")
        except FileNotFoundError:
            _LOGGER.warning(f"[{DOMAIN}] 📂 No token file yet — will request new token.")
            refresh_token_val = None

        if refresh_token_val:
            _LOGGER.info(f"[{DOMAIN}] 🔄 Trying to refresh using refresh_token...")
            success = _refresh_existing(client_id, client_secret, base_url, refresh_token_val, token_file)
            if success:
                return
            _LOGGER.warning(f"[{DOMAIN}] ⚠️ Refresh failed — requesting NEW token instead.")

        _LOGGER.info(f"[{DOMAIN}] 🔑 Requesting NEW token...")
        _request_new(client_id, client_secret, base_url, token_file)

    except Exception as e:
        _LOGGER.exception(f"[{DOMAIN}] 💥 Exception in refresh_token: {e}")

def _refresh_existing(client_id, client_secret, base_url, refresh_token_val, token_file):
    """Refresh existing token."""
    url_path = f"/v1.0/token/{refresh_token_val}"
    method = "GET"

    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    content_hash = hashlib.sha256("".encode()).hexdigest()
    string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
    sign_str = client_id + t + nonce + string_to_sign

    signature = hmac.new(
        client_secret.encode(),
        sign_str.encode(),
        hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": client_id,
        "sign": signature,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
    }

    url = f"{base_url}{url_path}"
    response = requests.get(url, headers=headers)
    _LOGGER.debug(f"[{DOMAIN}] 🔄 Refresh response: {response.status_code} | {response.text}")

    if response.status_code == 200 and response.json().get("success"):
        with open(token_file, "w") as f:
            json.dump(response.json()["result"], f, indent=2)
        _LOGGER.info(f"[{DOMAIN}] ✅ Token refreshed and saved.")
        return True

    _LOGGER.warning(f"[{DOMAIN}] ❌ Failed to refresh: {response.status_code} | {response.text}")
    return False

def _request_new(client_id, client_secret, base_url, token_file):
    """Request a new token."""
    url_path = "/v1.0/token?grant_type=1"
    method = "GET"

    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    content_hash = hashlib.sha256("".encode()).hexdigest()
    string_to_sign = f"{method}\n{content_hash}\n\n{url_path}"
    sign_str = client_id + t + nonce + string_to_sign

    signature = hmac.new(
        client_secret.encode(),
        sign_str.encode(),
        hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": client_id,
        "sign": signature,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
    }

    url = f"{base_url}{url_path}"
    response = requests.get(url, headers=headers)
    _LOGGER.debug(f"[{DOMAIN}] 🆕 New token response: {response.status_code} | {response.text}")

    if response.status_code == 200 and response.json().get("success"):
        with open(token_file, "w") as f:
            json.dump(response.json()["result"], f, indent=2)
        _LOGGER.info(f"[{DOMAIN}] ✅ New token fetched and saved.")
    else:
        _LOGGER.error(f"[{DOMAIN}] ❌ Failed to request new token: {response.status_code} | {response.text}")

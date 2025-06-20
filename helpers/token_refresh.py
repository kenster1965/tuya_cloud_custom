"""Tuya Cloud Custom: Token refresh + generic Tuya API helper."""

import json
import uuid
import time
import hmac
import hashlib
import logging
import requests
import yaml

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def refresh_token(secrets_file: str, token_file: str):
    """Safely refresh token with current secrets.yaml."""
    try:
        with open(secrets_file) as f:
            secrets = yaml.safe_load(f)
    except Exception as e:
        _LOGGER.exception("[%s] ❌ Failed to read secrets: %s", DOMAIN, e)
        return

    client_id = secrets["client_id"]
    client_secret = secrets["client_secret"]
    base_url = secrets["base_url"]

    url_path = "/v1.0/token?grant_type=1"
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    string_to_sign = f"{client_id}{t}{nonce}"
    sign = hmac.new(
        client_secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": client_id,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
    }

    url = f"{base_url}{url_path}"
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200 and response.json().get("success"):
        with open(token_file, "w") as f:
            json.dump(response.json()["result"], f)
        _LOGGER.info("[%s] ✅ Token refreshed.", DOMAIN)
    else:
        _LOGGER.error("[%s] ❌ Token refresh failed: %s", DOMAIN, response.text)


def send_tuya_command(hass, tuya_id: str, dp_code: str, value):
    """Generic helper to send Tuya command."""
    try:
        secrets = hass.data[DOMAIN]["secrets"]
        token_file = hass.data[DOMAIN]["token_file"]

        with open(token_file) as f:
            token_data = json.load(f)
        access_token = token_data["access_token"]

        client_id = secrets["client_id"]
        client_secret = secrets["client_secret"]
        base_url = secrets["base_url"]

        url_path = f"/v1.0/devices/{tuya_id}/commands"
        url = f"{base_url}{url_path}"

        payload = {
            "commands": [{"code": dp_code, "value": value}]
        }

        t = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        content_str = json.dumps(payload)
        content_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
        string_to_sign = f"POST\n{content_hash}\n\n{url_path}"
        sign_str = client_id + access_token + t + nonce + string_to_sign
        signature = hmac.new(
            client_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
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

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        _LOGGER.debug("[%s] ✅ Command %s=%s → %s", DOMAIN, dp_code, value, response.text)
        return response

    except Exception as e:
        _LOGGER.exception("[%s] ❌ Failed to send Tuya command: %s", DOMAIN, e)
        return None

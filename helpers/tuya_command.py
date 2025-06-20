"""Tuya Cloud Custom: Generic Tuya API Command Helper."""

import json
import uuid
import time
import hmac
import hashlib
import logging
import requests

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def send_tuya_command(hass, tuya_id: str, dp_code: str, value):
    """Generic helper to send a Tuya Cloud command."""
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

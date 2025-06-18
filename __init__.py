"""
Tuya Cloud Custom: __init__.py
-------------------------------
Main integration bootstrap.
Loads secrets, sets up token refresh loop, starts status polling,
and wires up switch, sensor, number platforms.
"""

import os
import yaml
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN
from .helpers.device_loader import load_tuya_devices
from .helpers.token_refresh import refresh_token
from .status import Status

_LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 📁 Paths
# ------------------------------------------------------------------------------
COMPONENT_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(COMPONENT_PATH, "config")
DEVICES_DIR = os.path.join(CONFIG_PATH, "devices")
#DEVICES_FILE = os.path.join(CONFIG_PATH, "tuya_devices.yaml")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

# ------------------------------------------------------------------------------
# Platforms to load
# ------------------------------------------------------------------------------
PLATFORMS = ["switch", "sensor", "number"]

# ------------------------------------------------------------------------------
# YAML fallback setup (unused for config_flow)
# ------------------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Optional legacy YAML fallback."""
    return True

# ------------------------------------------------------------------------------
# ✅ Setup from Config Entry
# ------------------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Cloud Custom from a Config Entry."""

    # ✅ 1️⃣ Load secrets async-safe
    secrets = await _check_secrets(hass)
    if secrets is None:
        return False

    # ✅ 2️⃣ Load devices async-safe
    devices = await hass.async_add_executor_job(load_tuya_devices, DEVICES_DIR)

    # ✅ 3️⃣ Store in hass.data FIRST
    hass.data[DOMAIN] = {
        "devices": devices,
        "secrets": secrets,
        "entities": {},  # shared registry for all platforms
        "token_file": TOKEN_FILE,
        "devices_file": DEVICES_FILE,
        "secrets_file": SECRETS_FILE,
    }

    # ✅ 4️⃣ Refresh token immediately (blocking IO → executor)
    await hass.async_add_executor_job(
        refresh_token, SECRETS_FILE, TOKEN_FILE
    )

    # ✅ 5️⃣ Schedule periodic token refresh
    interval = int(secrets.get("token_refresh", 110)) * 60  # min → sec

    async def _refresh_loop(_):
        _LOGGER.info(f"[{DOMAIN}] 🔄 Scheduled token refresh running...")
        await hass.async_add_executor_job(refresh_token, SECRETS_FILE, TOKEN_FILE)
        async_call_later(hass, interval, _refresh_loop)

    async_call_later(hass, interval, _refresh_loop)

    # ✅ 6️⃣ Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ✅ 7️⃣ Start Status polling AFTER everything is ready
    status = Status(hass)
    await status.async_start_polling()

    _LOGGER.info(f"[{DOMAIN}] ✅ Setup complete.")
    return True

# ------------------------------------------------------------------------------
# ✅ Clean unload
# ------------------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Config Entry cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok

# ------------------------------------------------------------------------------
# ✅ Async-safe secrets loader
# ------------------------------------------------------------------------------
async def _check_secrets(hass: HomeAssistant) -> dict | None:
    """Load secrets.yaml in executor, verify required keys."""

    if not os.path.isfile(SECRETS_FILE):
        hass.components.logger.error(
            f"[{DOMAIN}] ❌ Missing file: {SECRETS_FILE}"
        )
        return None

    try:
        secrets = await hass.async_add_executor_job(_read_secrets)

        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")
        token_refresh = secrets.get("token_refresh", 110)

        if not client_id or not client_secret or not base_url:
            hass.components.logger.error(
                f"[{DOMAIN}] ❌ Missing required keys in {SECRETS_FILE}"
            )
            return None

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "base_url": base_url,
            "token_refresh": token_refresh,
        }

    except Exception as e:
        hass.components.logger.error(
            f"[{DOMAIN}] 💥 Error reading {SECRETS_FILE}: {e}"
        )
        return None

def _read_secrets():
    """Blocking helper: read YAML from disk."""
    with open(SECRETS_FILE, "r") as f:
        return yaml.safe_load(f) or {}

"""
Tuya Cloud Custom: __init__.py
-------------------------------
Main entry for the custom integration.
Handles:
✅ Config Flow setup
✅ Devices loader (from config/devices/*.yaml)
✅ Periodic token refresh in executor
✅ Status poller
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
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

# ------------------------------------------------------------------------------
# Platforms to register
# ------------------------------------------------------------------------------
PLATFORMS = ["switch", "sensor", "number"]

# ------------------------------------------------------------------------------
# ✅ Legacy YAML fallback (optional)
# ------------------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML fallback — not used here."""
    return True

# ------------------------------------------------------------------------------
# ✅ Setup from Config Entry
# ------------------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup Tuya Cloud Custom from UI Config Entry."""

    # 1️⃣ Validate secrets.yaml safely
    secrets = await hass.async_add_executor_job(_check_secrets)
    if secrets is None:
        return False

    # 2️⃣ Load all device YAMLs safely
    devices = await hass.async_add_executor_job(load_tuya_devices, DEVICES_DIR)

    if not devices:
        _LOGGER.warning("[%s] ⚠️ No valid devices found in %s — nothing to set up.", DOMAIN, DEVICES_DIR)
        return False

    # 3️⃣ Store runtime data
    hass.data[DOMAIN] = {
        "secrets": secrets,
        "devices": devices,
        "entities": {},  # maps (device_id, dp_code) to entity objects
        "status": None,  # will be set below
        "token_file": TOKEN_FILE,
        "secrets_file": SECRETS_FILE,
    }

    # 4️⃣ Refresh token immediately (in executor)
    await hass.async_add_executor_job(refresh_token, SECRETS_FILE, TOKEN_FILE)

    # 5️⃣ Schedule periodic token refresh & force status update
    interval = int(secrets.get("token_refresh", 110)) * 60  # min → sec

    async def _refresh_loop(_):
        await hass.async_add_executor_job(refresh_token, SECRETS_FILE, TOKEN_FILE)

        if DOMAIN in hass.data and "status" in hass.data[DOMAIN]:
            status = hass.data[DOMAIN]["status"]
            await status.async_fetch_all_devices()

        async_call_later(hass, interval, _refresh_loop)

    async_call_later(hass, interval, _refresh_loop)

    # 6️⃣ Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 7️⃣ After all platforms done: start Status safely
    async def _start_status(_):
        status = Status(hass)
        hass.data[DOMAIN]["status"] = status
        await status.async_start_polling()

    # Let the loop finish, then start Status
    async_call_later(hass, 1, _start_status)

    _LOGGER.info("[%s] ✅ Tuya Cloud Custom setup complete!", DOMAIN)
    return True

# ------------------------------------------------------------------------------
# ✅ Unload cleanly
# ------------------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok

# ------------------------------------------------------------------------------
# ✅ Secrets check (executor safe)
# ------------------------------------------------------------------------------
def _check_secrets() -> dict | None:
    """Check secrets file directly, safe for executor only."""
    if not os.path.isfile(SECRETS_FILE):
        _LOGGER.error("[%s] ❌ Missing %s", DOMAIN, SECRETS_FILE)
        return None

    try:
        with open(SECRETS_FILE, "r") as f:
            secrets = yaml.safe_load(f) or {}

        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")
        token_refresh = secrets.get("token_refresh", 110)

        if not client_id or not client_secret or not base_url:
            _LOGGER.error("[%s] ❌ Required fields missing in %s", DOMAIN, SECRETS_FILE)
            return None

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "base_url": base_url,
            "token_refresh": token_refresh,
        }

    except Exception as e:
        _LOGGER.exception("[%s] ❌ Error loading %s: %s", DOMAIN, SECRETS_FILE, e)
        return None

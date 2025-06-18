"""
Tuya Cloud Custom: __init__.py
-------------------------------
Entry point for your custom integration.
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
# Paths
# ------------------------------------------------------------------------------
COMPONENT_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(COMPONENT_PATH, "config")
DEVICES_FILE = os.path.join(CONFIG_PATH, "tuya_devices.yaml")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

# Platforms
PLATFORMS = ["switch", "sensor", "number"]


# ------------------------------------------------------------------------------
# YAML fallback setup (rare)
# ------------------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Legacy YAML fallback — unused in config_flow mode."""
    return True


# ------------------------------------------------------------------------------
# ✅ Setup from Config Entry
# ------------------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Cloud Custom from Config Entry."""

    # ✅ 1️⃣ Load secrets YAML
    secrets = _check_secrets(hass)
    if secrets is None:
        return False

    # ✅ 2️⃣ Load devices YAML
    devices = await hass.async_add_executor_job(load_tuya_devices, DEVICES_FILE)

    # ✅ 3️⃣ Store all in hass.data FIRST!
    hass.data[DOMAIN] = {
        "devices": devices,
        "secrets": secrets,
        "entities": {},  # all switch/sensor/number track themselves here
        "token_file": TOKEN_FILE,
        "devices_file": DEVICES_FILE,
        "secrets_file": SECRETS_FILE,
    }

    # ✅ 4️⃣ Refresh token immediately
    await hass.async_add_executor_job(
        refresh_token, SECRETS_FILE, TOKEN_FILE
    )

    # ✅ 5️⃣ Schedule periodic token refresh
    interval = int(secrets.get("token_refresh", 110)) * 60  # min -> sec

    async def _refresh_loop(_):
        _LOGGER.info(f"[{DOMAIN}] 🔄 Scheduled token refresh running...")
        await hass.async_add_executor_job(refresh_token, SECRETS_FILE, TOKEN_FILE)
        async_call_later(hass, interval, _refresh_loop)

    async_call_later(hass, interval, _refresh_loop)

    # ✅ 6️⃣ Forward all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ✅ 7️⃣ Start status polling — always AFTER hass.data is populated!
    status = Status(hass)
    await status.async_start_polling()

    _LOGGER.info(f"[{DOMAIN}] ✅ Setup complete.")
    return True


# ------------------------------------------------------------------------------
# ✅ Unload Config Entry cleanly
# ------------------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload this Config Entry properly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok


# ------------------------------------------------------------------------------
# ✅ Helper: Validate secrets.yaml exists and has keys
# ------------------------------------------------------------------------------
def _check_secrets(hass: HomeAssistant) -> dict | None:
    """Load secrets.yaml and verify required fields exist."""

    if not os.path.isfile(SECRETS_FILE):
        hass.components.logger.error(
            f"[{DOMAIN}] ❌ Missing file: {SECRETS_FILE}"
        )
        return None

    try:
        with open(SECRETS_FILE, "r") as f:
            secrets = yaml.safe_load(f) or {}

        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")
        token_refresh = secrets.get("token_refresh", 110)

        if not client_id or not client_secret or not base_url:
            hass.components.logger.error(
                f"[{DOMAIN}] ❌ Missing client_id, client_secret or base_url in {SECRETS_FILE}"
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

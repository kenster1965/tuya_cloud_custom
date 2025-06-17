import os
import yaml
import logging
import asyncio

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
DEVICES_FILE = os.path.join(CONFIG_PATH, "tuya_devices.yaml")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

# ------------------------------------------------------------------------------
# Platforms
# ------------------------------------------------------------------------------
PLATFORMS = ["switch", "sensor", "number"]

# ------------------------------------------------------------------------------
# 🏁 SETUP for legacy YAML (optional fallback)
# ------------------------------------------------------------------------------

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Tuya Cloud Custom using YAML if present.

    This is now a placeholder since config_entry is the preferred way.
    """
    return True

# ------------------------------------------------------------------------------
# ✅ Setup from Config Flow entry
# ------------------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Cloud Custom from a Config Entry."""

    # ✅ 1️⃣ Load and validate secrets
    secrets = await hass.async_add_executor_job(_check_secrets, SECRETS_FILE)
    if secrets is None:
        return False

    # ✅ 2️⃣ Load devices YAML
    devices = await hass.async_add_executor_job(load_tuya_devices, DEVICES_FILE)

    # ✅ 3️⃣ Store everything in hass.data for runtime sharing
    hass.data[DOMAIN] = {
        "devices": devices,
        "secrets": secrets,
        "entities": {},
        "token_file": TOKEN_FILE,
        "devices_file": DEVICES_FILE,
        "secrets_file": SECRETS_FILE,
    }

    # ✅ 4️⃣ Refresh token immediately (in executor because it's blocking)
    hass.async_add_executor_job(refresh_token)

    # ✅ 5️⃣ Schedule periodic token refresh
    interval = int(secrets.get("token_refresh", 110)) * 60  # min → sec

    async def _refresh_loop(_):
        await hass.async_add_executor_job(refresh_token)
        async_call_later(hass, interval, _refresh_loop)

    async_call_later(hass, interval, _refresh_loop)

    # ✅ 6️⃣ Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ✅ 7️⃣ Start TuyaStatus polling
    status = Status(hass)
    await status.async_start_polling()

    _LOGGER.info("[%s] ✅ Setup complete", DOMAIN)
    return True


# ------------------------------------------------------------------------------
# ✅ Unload Config Entry cleanly
# ------------------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Config Entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok

# ------------------------------------------------------------------------------
# ✅ Helper: check secrets.yaml exists and has required fields
# ------------------------------------------------------------------------------
def _check_secrets(filepath) -> dict | None:
    """Verify secrets.yaml has required fields."""
    if not os.path.isfile(filepath):
        _LOGGER.error(f"[{DOMAIN}] ❌ Missing required file: {filepath}")
        return None

    try:
        with open(filepath, "r") as f:
            secrets = yaml.safe_load(f) or {}

        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")
        token_refresh = secrets.get("token_refresh", 110)

        if not client_id or not client_secret or not base_url:
            _LOGGER.error(f"[{DOMAIN}] ❌ Required fields missing in {filepath}")
            return None

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "base_url": base_url,
            "token_refresh": token_refresh,
        }

    except Exception as e:
        _LOGGER.error(f"[{DOMAIN}] 💥 Error reading {filepath}: {e}")
        return None

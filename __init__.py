import os
import yaml
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.discovery import async_load_platform

from .helpers.tuya_device_loader import load_tuya_devices
from .helpers.tuya_token_refresh import refresh_token
from .const import DOMAIN

# ------------------------------------------------------------------------------
# 📁 Paths
# ------------------------------------------------------------------------------

COMPONENT_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(COMPONENT_PATH, "config")
DEVICES_FILE = os.path.join(CONFIG_PATH, "tuya_devices.yaml")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

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

    # 1️⃣ Check secrets.yaml exists and valid
    if not _check_secrets(hass):
        return False

    # 2️⃣ Load devices YAML
    devices = load_tuya_devices(DEVICES_FILE)
    hass.data[DOMAIN] = {"devices": devices}

    # 3️⃣ Refresh Tuya token once at startup
    hass.async_add_executor_job(refresh_token)

    # 4️⃣ Forward entry to each platform — must await!
    await asyncio.gather(
        *[
            hass.config_entries.async_forward_entry_setup(entry, platform)
            for platform in PLATFORMS
        ]
    )

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
# ✅ Helper: check secrets.yaml exists and has required keys
# ------------------------------------------------------------------------------

def _check_secrets(hass: HomeAssistant) -> bool:
    """Verify secrets.yaml has required fields."""
    if not os.path.isfile(SECRETS_FILE):
        hass.components.logger.error(
            f"[{DOMAIN}] ❌ Missing required file: {SECRETS_FILE}"
        )
        return False

    try:
        with open(SECRETS_FILE, "r") as f:
            secrets = yaml.safe_load(f) or {}
        client_id = secrets.get("client_id")
        client_secret = secrets.get("client_secret")
        base_url = secrets.get("base_url")
        if not client_id or not client_secret or not base_url:
            hass.components.logger.error(
                f"[{DOMAIN}] ❌ Required fields missing: client_id, client_secret, or base_url in {SECRETS_FILE}"
            )
            return False
    except Exception as e:
        hass.components.logger.error(
            f"[{DOMAIN}] 💥 Error reading {SECRETS_FILE}: {e}"
        )
        return False

    return True

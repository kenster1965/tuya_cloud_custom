import os
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.discovery import async_load_platform

from .helpers.tuya_device_loader import load_tuya_devices
from .helpers.tuya_token_refresh import refresh_token
from .const import DOMAIN

COMPONENT_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(COMPONENT_PATH, "config")
DEVICES_FILE = os.path.join(CONFIG_PATH, "tuya_devices.yaml")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

PLATFORMS = ["switch", "sensor", "number"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Tuya Cloud Custom from YAML (legacy)."""
    return True  # nothing for legacy YAML anymore

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Cloud Custom from a Config Entry."""

    # ✅ Check secrets.yaml
    if not _check_secrets(hass):
        return False

    devices = load_tuya_devices(DEVICES_FILE)
    hass.data[DOMAIN] = {"devices": devices}

    # Refresh token once at startup
    hass.async_add_executor_job(refresh_token)

    # Setup platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Config Entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok

def _check_secrets(hass: HomeAssistant) -> bool:
    if not os.path.isfile(SECRETS_FILE):
        hass.components.logger.error(f"[{DOMAIN}] ❌ Missing secrets.yaml")
        return False
    try:
        with open(SECRETS_FILE, "r") as f:
            secrets = yaml.safe_load(f)
        if not all(secrets.get(k) for k in ("client_id", "client_secret", "base_url")):
            hass.components.logger.error(f"[{DOMAIN}] ❌ Required fields missing in secrets.yaml")
            return False
    except Exception as e:
        hass.components.logger.error(f"[{DOMAIN}] 💥 Error reading secrets.yaml: {e}")
        return False
    return True

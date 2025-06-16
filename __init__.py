import os
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from .helpers.tuya_device_loader import load_tuya_devices
from .helpers.tuya_token_refresh import refresh_token

# ------------------------------------------------------------------------------------
# DOMAIN + PATHS
# ------------------------------------------------------------------------------------

DOMAIN = "tuya_cloud_custom"

# Root path to THIS custom component
HERE = os.path.dirname(__file__)
PARENT = os.path.abspath(os.path.join(HERE, ".."))

COMPONENT_PATH = os.path.dirname(__file__)

# Subfolders
#CONFIG_PATH = os.path.join(COMPONENT_PATH, "config")

# Config files
CONFIG_PATH = os.path.join(PARENT, "config")
TOKEN_FILE = os.path.join(CONFIG_PATH, "tuya_token.json")
SECRETS_FILE = os.path.join(CONFIG_PATH, "secrets.yaml")

# Platforms provided by this integration
PLATFORMS = ["switch", "sensor", "number"]

# ------------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------------

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Tuya Cloud Custom component."""

    # Load enabled devices from YAML
    devices = load_tuya_devices(DEVICES_FILE)
    hass.data[DOMAIN] = {
        "devices": devices
    }

    # Refresh Tuya token on startup
    hass.async_add_executor_job(refresh_token)

    # Load the defined platforms (switch, sensor, number)
    for platform in PLATFORMS:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True

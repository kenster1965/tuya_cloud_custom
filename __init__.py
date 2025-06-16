from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from .tuya_device_loader import load_tuya_devices

DOMAIN = "tuya_cloud_custom"
PLATFORMS = ["sensor", "switch", "number"]

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data[DOMAIN] = {
        "devices": load_tuya_devices(hass.config.path("share"))
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True

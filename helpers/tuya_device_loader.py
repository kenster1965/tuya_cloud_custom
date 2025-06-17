import yaml
import logging

_LOGGER = logging.getLogger(__name__)

def load_tuya_devices(devices_file):
    """
    Load Tuya devices from YAML, skipping disabled ones.
    Logs and returns empty list on failure.
    """
    try:
        with open(devices_file, "r") as f:
            data = yaml.safe_load(f) or {}
            return [d for d in data.get("devices", []) if d.get("enabled", True)]
    except Exception as e:
        _LOGGER.error(f"Failed to load Tuya devices from {devices_file}: {e}")
        return []

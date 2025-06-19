import os
import yaml
import logging
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def load_tuya_devices(devices_dir: str) -> list:
    """
    Load all Tuya devices from individual YAML files in a folder.
    Each file must contain:
    - one 'device:' block
    - one or more entity blocks: switch:, sensor:, number: ...
    """

    devices = []

    if not os.path.isdir(devices_dir):
        _LOGGER.error(f"[{DOMAIN}] ❌ Devices directory not found: {devices_dir}")
        return devices

    for file_name in os.listdir(devices_dir):
        if not file_name.endswith(".yaml"):
            continue

        file_path = os.path.join(devices_dir, file_name)

        try:
            with open(file_path, "r") as f:
                yaml_data = yaml.safe_load(f) or []
        except Exception as e:
            _LOGGER.error(f"[{DOMAIN}] ❌ Failed to load {file_name}: {e}")
            continue

        # Find the device block
        device_block = None
        entity_blocks = []

        for item in yaml_data:
            if "device" in item:
                device_block = item["device"]
            else:
                # must be a switch, sensor, number, etc.
                entity_blocks.append(item)

        if not device_block:
            _LOGGER.warning(f"[{DOMAIN}] ⚠️ No 'device:' block found in {file_name} — skipping.")
            continue

        if not device_block.get("enabled", True):
            _LOGGER.info(f"[{DOMAIN}] ⏹️ Skipping disabled device in {file_name}.")
            continue

        ha_name = device_block.get("ha_name", "unknown")
        device_block["entities"] = []

        for ent in entity_blocks:
            if not isinstance(ent, dict) or len(ent) != 1:
                _LOGGER.warning(f"[{DOMAIN}] ⚠️ Invalid entity format in {file_name}, skipping entity: {ent}")
                continue

            platform, conf = next(iter(ent.items()))
            if not conf.get("enabled", True):
                continue

            conf["platform"] = platform  # track platform type explicitly
            device_block["entities"].append(conf)

        _LOGGER.info(
            f"[{DOMAIN}] ✅ Loaded {ha_name} from {file_name} with "
            f"{len(device_block['entities'])} entities."
        )

        devices.append(device_block)

    if not devices:
        _LOGGER.warning(f"[{DOMAIN}] ⚠️ No valid enabled devices found in {devices_dir}")

    return devices

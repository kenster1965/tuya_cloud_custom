import os
import yaml
import logging

_LOGGER = logging.getLogger(__name__)


def load_tuya_devices(devices_dir: str) -> list:
    """
    Load all Tuya device YAMLs from the given directory.

    Each file should be:
      - device:
          ha_name: ...
          ...
      - switch:
          ...
      - sensor:
          ...
      - number:
          ...
    """

    all_devices = []

    if not os.path.isdir(devices_dir):
        _LOGGER.warning(f"[tuya_cloud_custom] ⚠️ Devices folder not found: {devices_dir}")
        return all_devices

    for fname in sorted(os.listdir(devices_dir)):
        if not fname.endswith(".yaml"):
            continue

        full_path = os.path.join(devices_dir, fname)
        try:
            with open(full_path, "r") as f:
                doc = yaml.safe_load(f) or []

            if not isinstance(doc, list):
                _LOGGER.error(f"[tuya_cloud_custom] ❌ Invalid YAML in {fname}: must be a list of blocks")
                continue

            # Extract main device
            device_block = next((entry.get("device") for entry in doc if "device" in entry), None)
            if not device_block:
                _LOGGER.error(f"[tuya_cloud_custom] ❌ No 'device:' block in {fname}")
                continue

            if not device_block.get("enabled", True):
                _LOGGER.info(f"[tuya_cloud_custom] ⏹️ Skipped disabled device in {fname}")
                continue

            # Extract all DPS
            dps = []
            for entry in doc:
                for key, value in entry.items():
                    if key == "device":
                        continue
                    if not isinstance(value, dict):
                        _LOGGER.warning(f"[tuya_cloud_custom] ⚠️ Skipped malformed block '{key}' in {fname}")
                        continue
                    if not value.get("enabled", True):
                        _LOGGER.info(f"[tuya_cloud_custom] ⏹️ Skipped disabled {key} in {fname}")
                        continue
                    dp = value.copy()
                    dp["platform"] = key  # Mark the entity type
                    dps.append(dp)

            device_block["dps"] = dps

            all_devices.append(device_block)

            _LOGGER.info(f"[tuya_cloud_custom] 📄 Loaded device file: {fname}")

        except Exception as e:
            _LOGGER.exception(f"[tuya_cloud_custom] ❌ Error reading {fname}: {e}")

    return all_devices

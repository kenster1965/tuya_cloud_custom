"""
Tuya Cloud Custom - Device Loader

Loads all YAML files in config/devices/ and validates required structure.
Supports multi-DP platforms like climate, plus switch, sensor, number.
"""

import os
import yaml
import logging

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def load_tuya_devices(devices_dir: str) -> list:
    """Load all device YAMLs in the given directory."""

    devices = []

    if not os.path.isdir(devices_dir):
        _LOGGER.error("[%s] ❌ Devices directory does not exist: %s", DOMAIN, devices_dir)
        return devices

    for file_name in os.listdir(devices_dir):
        if not file_name.endswith(".yaml"):
            continue

        file_path = os.path.join(devices_dir, file_name)

        try:
            with open(file_path, "r") as f:
                content = yaml.safe_load(f)
        except Exception as e:
            _LOGGER.exception("[%s] ❌ Error reading %s: %s", DOMAIN, file_name, e)
            continue

        if not content or not isinstance(content, list):
            _LOGGER.warning("[%s] ⚠️ File %s is not a list of blocks — skipping.", DOMAIN, file_name)
            continue

        # Extract device info + all platforms in this file
        device_conf = None
        entities = []

        for block in content:
            if "device" in block:
                device_conf = block["device"]
            elif "climate" in block:
                dp = block["climate"]
                # ✅ New required top-level keys
                required_keys = ["current_temperature", "target_temperature", "hvac_mode"]
                missing = [k for k in required_keys if k not in dp]
                valid = True

                # Also ensure sub-keys exist:
                if "current_temperature" in dp and "code" not in dp["current_temperature"]:
                    missing.append("current_temperature.code")
                    valid = False
                if "target_temperature" in dp and "code" not in dp["target_temperature"]:
                    missing.append("target_temperature.code")
                    valid = False
                if "hvac_mode" in dp and not isinstance(dp["hvac_mode"], dict):
                    missing.append("hvac_mode must be a dict of modes")
                    valid = False
                elif "hvac_mode" in dp and not any(isinstance(v, dict) for v in dp["hvac_mode"].values()):
                    missing.append("hvac_mode must define at least one mode with dict fields")
                    valid = False
                if missing:
                    _LOGGER.error("[%s] ❌ Climate block missing keys %s in %s", DOMAIN, missing, file_name)
                    continue
                dp["platform"] = "climate"
                entities.append(dp)
            elif "switch" in block:
                dp = block["switch"]
                dp["platform"] = "switch"
                entities.append(dp)
            elif "sensor" in block:
                dp = block["sensor"]
                dp["platform"] = "sensor"
                entities.append(dp)
            elif "number" in block:
                dp = block["number"]
                dp["platform"] = "number"
                entities.append(dp)
            else:
                _LOGGER.warning("[%s] ⚠️ Unknown block in %s: %s", DOMAIN, file_name, block)

        if not device_conf:
            _LOGGER.error("[%s] ❌ File %s missing top-level 'device:' block!", DOMAIN, file_name)
            continue

        if not entities:
            _LOGGER.warning("[%s] ⚠️ No valid entities found in %s — skipping.", DOMAIN, file_name)
            continue

        # ✅ Compose device entry
        device_conf.setdefault("enabled", True)
        device_conf.setdefault("poll_interval", 60)
        device_conf["entities"] = entities

        devices.append(device_conf)
        _LOGGER.info("[%s] ✅ Loaded %s with %s entities from %s",
                     DOMAIN, device_conf.get("tuya_device_id"), len(entities), file_name)

    return devices

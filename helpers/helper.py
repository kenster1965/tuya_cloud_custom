"""
Tuya Cloud Custom - Helper utilities for building entities and devices.
"""

import re
import logging
from ..const import DOMAIN, VALID_ENTITY_CATEGORIES, VALID_SENSOR_CLASSES
from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)


def sanitize(value: str) -> str:
    """Sanitize a string for HA entity_id usage."""
    value = value.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "_", value)


def build_entity_attrs(device: dict, dp: dict, platform: str) -> dict:
    """Build standard HA entity attributes from device & dp config."""
    attrs = {}

    # Always use stable unique_id: tuya_device_id + "_" + code
    code = sanitize(dp.get("code", "unknown"))
    unique_id = f"{device['tuya_device_id']}_{code}"
    attrs["unique_id"] = unique_id

    # Only set 'name' if a friendly_name is explicitly provided in the DP
    if "friendly_name" in dp:
        attrs["name"] = dp["friendly_name"]

    # ✅ Device class + unit
    device_class = dp.get("device_class")
    unit = dp.get("unit_of_measurement")

    if device_class:
        if platform == "sensor" and device_class not in VALID_SENSOR_CLASSES:
            _LOGGER.warning(
                "[%s] ⚠️ Invalid device_class '%s' for sensor. Ignoring.",
                DOMAIN, device_class
            )
        else:
            attrs["device_class"] = device_class
            if unit:
                attrs["native_unit_of_measurement"] = unit

    # ✅ Entity category, if valid
    ec = dp.get("entity_category")
    if ec in VALID_ENTITY_CATEGORIES:
        attrs["entity_category"] = EntityCategory(ec)
    elif ec:
        _LOGGER.warning(
            "[%s] ⚠️ Invalid entity_category: %s (DP: %s) — ignoring.",
            DOMAIN, ec, dp.get("code")
        )

    return attrs


def build_device_info(device: dict) -> dict:
    """Link entity to its Device."""
    return {
        "identifiers": {(DOMAIN, device["tuya_device_id"])},
        "name": device.get("friendly_name") or device.get("ha_name"),
        "manufacturer": "Tuya",
        "model": device.get("category", "Unknown"),
    }

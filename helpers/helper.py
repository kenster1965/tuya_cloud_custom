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

    tuya_id = device["tuya_device_id"]
    code = sanitize(dp.get("code", "unknown"))

    # ✅ Stable unique_id
    attrs["unique_id"] = f"{tuya_id}_{code}"

    # ✅ No friendly name for the entity: user sets it in UI

    # ✅ Device class & unit if valid
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

    # ✅ Entity category
    ec = dp.get("entity_category")
    if ec in VALID_ENTITY_CATEGORIES:
        attrs["entity_category"] = EntityCategory(ec)
    elif ec:
        _LOGGER.warning(
            "[%s] ⚠️ Invalid entity_category: %s (DP: %s) — ignoring.",
            DOMAIN, ec, code
        )

    return attrs

def build_device_info(device: dict) -> dict:
    """Link entity to its Device in HA."""
    return {
        "identifiers": {(DOMAIN, device["tuya_device_id"])},
        "name": device.get("friendly_name"),  # optional: shows nicely in Devices panel
        "manufacturer": "Tuya",
        "model": device.get("tuya_category", "Unknown"),
    }

"""
Tuya Cloud Custom - Helper utilities for building entities and devices.

Version: 2025.07.03
Author: Ken Jensen & Assistant
Description:
  - Provides safe attribute builders for custom Tuya Cloud Home Assistant integration.
  - Ensures robust unique_id, entity_id, user-friendly naming, and collision-free device info.
"""

import re
import logging
from ..const import DOMAIN, VALID_ENTITY_CATEGORIES, VALID_SENSOR_CLASSES
from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)


def sanitize(value: str) -> str:
    """
    Sanitize a string for use in HA entity_id or unique_id.

    - Lowercase
    - Spaces → underscore
    - Remove any non-alphanumeric or underscore chars.
    """
    value = value.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "_", value)


def build_entity_attrs(device: dict, dp: dict, platform: str) -> dict:
    """
    Build standard HA entity attributes for a given DP.

    - For climate: uses dp["unique_id"] as both unique_id + base name.
    - For other platforms: uses tuya_device_id + code.
    Ensures:
      - Stable unique_id (tuya_device_id + code)
      - Friendly display name: DP code → Title Case
      - Valid device class & unit
      - Valid entity category
      - Icon support (optional)
    """
    attrs = {}

    tuya_id = device["tuya_device_id"]

    if platform == "climate":
        base_id = sanitize(dp.get("unique_id", "unknown"))
    else:
        base_id = sanitize(dp.get("code", "unknown"))

    attrs["unique_id"] = f"{tuya_id}_{base_id}"

    # ✅ Clean pretty name: snake_case → Title Case
    auto_name = base_id.replace("_", " ").title()
    attrs["name"] = dp.get("name") or auto_name

    # ✅ Icon support
    if "icon" in dp:
        attrs["icon"] = dp["icon"]
        _LOGGER.debug("[%s] 🖼️ Icon for %s: %s", DOMAIN, attrs["unique_id"], dp["icon"])

    # ✅ Other attributes (device_class, unit, etc.) only for non-climate
    if platform != "climate":
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

        ec = dp.get("entity_category")
        if ec in VALID_ENTITY_CATEGORIES:
            attrs["entity_category"] = EntityCategory(ec)
        elif ec:
            _LOGGER.warning(
                "[%s] ⚠️ Invalid entity_category: %s (DP: %s) — ignoring.",
                DOMAIN, ec, base_id
            )

    return attrs


def build_device_info(device: dict) -> dict:
    """
    Build robust HA Device info for Tuya Cloud Custom.

    - `identifiers` pins the unique Device Registry ID (always tuya_device_id)
    - `name` = tuya_device_id (controls slug for stable entity_id)
    - `suggested_area` = friendly_name for better UI, but does NOT affect entity_id
    - `model` = "prod:<product_id> | cat:<category>" with safe fallback
    """
    tuya_id = device["tuya_device_id"]
    friendly_name = device.get("friendly_name", tuya_id)

    product_id = device.get("tuya_product_id", "unknown")
    category = device.get("tuya_category", "unknown")

    model = f"prod:{product_id} | cat:{category}"

    return {
        "identifiers": {(DOMAIN, tuya_id)},  # 🗝️ real unique Device ID
        "name": friendly_name,               # 🗝️ used for auto entity_id slug
        "manufacturer": "Tuya",
        "model": model
    }

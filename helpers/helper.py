"""
Tuya Cloud Custom: Shared Helper Functions
------------------------------------------
Reusable utilities for building entity attributes & device info.
"""

import re
from homeassistant.helpers.entity import EntityCategory
from ..const import DOMAIN

# Only valid HA entity categories
VALID_ENTITY_CATEGORIES = {"diagnostic", "config"}

def sanitize(value: str) -> str:
    """Sanitize a string for HA entity_id usage."""
    value = value.replace(" ", "_").lower()
    return re.sub(r"[^a-z0-9_]+", "_", value)

def build_entity_attrs(device, dp, platform: str, logger=None) -> dict:
    """Build safe attributes for a DP entity."""
    ha_name = sanitize(device.get("ha_name", "unknown"))
    dp_code = sanitize(dp["code"])

    name = f"{ha_name}_{dp_code}"
    unique_id = f"{platform}.{name}"

    attrs = {
        "name": f"{ha_name} {dp_code}".replace("_", " ").title(),
        "unique_id": unique_id
    }

    if "device_class" in dp:
        attrs["device_class"] = dp["device_class"]

    ec = dp.get("entity_category")
    if ec in VALID_ENTITY_CATEGORIES:
        attrs["entity_category"] = EntityCategory(ec)
    elif ec:
        if logger:
            logger.warning(f"[{DOMAIN}] ⚠️ Ignored invalid entity_category: {ec}")

    if platform == "number":
        attrs["min"] = dp.get("min_value")
        attrs["max"] = dp.get("max_value")
        attrs["step"] = dp.get("step_size")

    if "unit" in dp:
        attrs["unit"] = dp["unit"]

    return attrs

def build_device_info(device) -> dict:
    """Link all entities to a single HA Device Registry item."""
    return {
        "identifiers": {(DOMAIN, device["tuya_device_id"])},
        "name": device.get("ha_name", "Tuya Cloud Device"),
        "manufacturer": "Tuya",
        "model": device.get("category", "unknown")
    }

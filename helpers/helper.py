import re
from ..const import DOMAIN
from homeassistant.helpers.entity import EntityCategory

# Allowed HA entity categories
VALID_ENTITY_CATEGORIES = {
    "diagnostic": EntityCategory.DIAGNOSTIC,
    "config": EntityCategory.CONFIG,
}

def sanitize(value: str, logger=None):
    """Slugify a string for HA entity_id safety."""
    original = value
    cleaned = value.lower().replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    if logger and original != cleaned:
        logger.warning(f"[{DOMAIN}] Sanitized: '{original}' → '{cleaned}'")
    return cleaned


def build_entity_attrs(device, dp, platform: str, logger=None):
    """
    Build attributes for an HA entity:
    - ID uses ha_name + code only (never friendly name)
    - UI name uses ha_name + code by default
    - Skips bad entity_category with a log
    """

    ha_name = sanitize(device["ha_name"], logger)
    dp_code = sanitize(dp.get("code") or "unknown", logger)

    unique_id = f"{ha_name}_{dp_code}"
    entity_id = f"{platform}.{unique_id}"

    # Simple default UI name
    friendly_name = f"{ha_name} {dp_code}"

    attrs = {
        "entity_id": entity_id,
        "unique_id": unique_id,
        "name": friendly_name,
    }

    if "device_class" in dp:
        attrs["device_class"] = dp["device_class"]

    ec = dp.get("entity_category")
    if ec in VALID_ENTITY_CATEGORIES:
        attrs["entity_category"] = VALID_ENTITY_CATEGORIES[ec]
    elif ec and logger:
        logger.warning(
            f"[{DOMAIN}] Ignored invalid entity_category '{ec}' for DP '{dp_code}'. "
            f"Must be one of: {list(VALID_ENTITY_CATEGORIES.keys())}."
        )

    if "unit" in dp:
        attrs["unit"] = dp["unit"]

    if platform == "number":
        attrs["min"] = dp.get("min_value")
        attrs["max"] = dp.get("max_value")
        attrs["step"] = dp.get("step_size")

    return attrs


def build_device_info(device):
    """Return HA Device Registry info so multiple entities group together."""
    return {
        "identifiers": {(DOMAIN, device["tuya_device_id"])},
        "name": device["ha_name"],
        "manufacturer": "Tuya",
        "model": device.get("category", "Unknown"),
        "sw_version": str(device.get("version", "unknown")),
    }

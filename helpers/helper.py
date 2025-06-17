import re

# Only HA-supported categories
VALID_ENTITY_CATEGORIES = {"diagnostic", "config"}

def sanitize(value: str, logger=None) -> str:
    """
    Sanitize a string for HA entity_id usage:
    - lowercases
    - replaces spaces with underscores
    - replaces invalid chars with underscores
    - logs if any change is made
    """
    original = value
    cleaned = value.lower().replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)

    if original != cleaned and logger:
        logger.warning(
            f"[tuya_cloud_custom] Sanitized value: '{original}' → '{cleaned}'"
        )

    return cleaned


def build_entity_attrs(device, dp, platform: str, logger=None):
    """
    Build clean entity attributes for Tuya Cloud Custom:
    - Good unique_id & entity_id
    - Friendly name for UI
    - Only valid entity_category
    - Optional log warnings for sanitizing & invalid categories
    """
    ha_base = sanitize(device["ha_name"], logger)
    dp_code = sanitize(dp["code"], logger)
    unique_id = f"{ha_base}_{dp_code}"
    entity_id = f"{platform}.{unique_id}"

    friendly_name = f"{device.get('friendly_name', ha_base)} - {dp.get('friendly_name', dp['code'])}"

    attrs = {
        "entity_id": entity_id,
        "unique_id": unique_id,
        "name": friendly_name,
    }

    if "device_class" in dp:
        attrs["device_class"] = dp["device_class"]

    ec = dp.get("entity_category")
    if ec in VALID_ENTITY_CATEGORIES:
        attrs["entity_category"] = ec
    elif ec and logger:
        logger.warning(
            f"[tuya_cloud_custom] Ignored invalid entity_category '{ec}' "
            f"for DP '{dp_code}'. Must be one of: {VALID_ENTITY_CATEGORIES}."
        )

    if "unit" in dp:
        attrs["unit"] = dp["unit"]

    if platform == "number":
        attrs["min"] = dp.get("min_value")
        attrs["max"] = dp.get("max_value")
        attrs["step"] = dp.get("step_size")

    return attrs

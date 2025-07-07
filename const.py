"""Tuya Cloud Custom - Constants."""

# Base component constants
DOMAIN = "tuya_cloud_custom"
VERSION = "2025.06.25"

# Valid HA entity categories
VALID_ENTITY_CATEGORIES = {
    "config",
    "diagnostic",
}

# Valid HA device classes for sensor and number
VALID_SENSOR_CLASSES = {
    # Temperature & environment
    "temperature", "humidity", "pressure", "illuminance", "signal_strength",
    "battery",

    # Energy & power
    "power", "energy", "voltage", "current", "monetary",

    # Air quality
    "aqi", "pm25", "carbon_monoxide", "carbon_dioxide", "gas", "nitrogen_dioxide",
    "ozone", "sulphur_dioxide", "volatile_organic_compounds",

    # Other common
    "timestamp",
}

# Supported platforms
SUPPORTED_PLATFORMS = {"switch", "sensor", "number", "climate"}


tuya_devices.yaml

Field in YAML	Purpose
ha_name	        HA entity ID (should be unique)
tuya_device_id	Device ID for Tuya API (used in commands)
friendly_name	User-facing name for cards/entities
dps[].id	    Data Point (DP) ID for Tuya commands
dps[].code	    P code name (human-readable)
dps[].platform	HA platform type: sensor, switch, etc.
enabled	Whether to include the device/dp

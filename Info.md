
tuya_devices.yaml

Field in YAML	Purpose
ha_name	        HA entity ID (should be unique)
tuya_device_id	Device ID for Tuya API (used in commands)
friendly_name	User-facing name for cards/entities
dps[].id	    Data Point (DP) ID for Tuya commands
dps[].code	    DP code name (human-readable)
dps[].platform	HA platform type: sensor, switch, etc.
enabled	Whether to include the device/dp


tuya_cloud_custom/
├── config/              <-- configs & secrets
├── helpers/             <-- helper scripts
├── platform files       <-- number.py, sensor.py, switch.py
├── __init__.py
├── manifest.json
├── tuya_status.py       <-- maybe your polling logic
└── Info.md

__init__.py	                        Loads the YAML once & stores the list in hass.data
switch.py, sensor.py, number.py	    Use that list to instantiate real HA Entity subclasses

__init__.py → load YAML → store in hass.data
platform.py (e.g., switch.py) → read hass.data → create Entities

Later I want register this as a HA serviceto tuya_cloud_custom.refresh_token for easy automation.

entity_category should either be: a valid string like "diagnostic" or "config",

Field	                Meaning
ha_name	                Local ID for your integration.
tuya_device_id	        The real Tuya Cloud hardware ID (globally unique).
category	            Tuya’s standard type code for that device class.
local_ip + local_key	Used for LAN/local protocol, not relevant for Device Registry.

custom_components/tuya_cloud_custom/
├── __init__.py               ✅ main integration bootstrap
├── manifest.json             ✅ your existing valid manifest
├── const.py                  ✅ contains: DOMAIN = "tuya_cloud_custom"
├── config_flow.py            ✅ minimal config flow if you use it
├── status.py                 ✅ handles periodic polling
├── switch.py                 ✅ your switch platform
├── sensor.py                 ✅ your sensor platform
├── number.py                 ✅ your number platform
├── helpers/
│   ├── helper.py             ✅ shared build helpers
│   ├── token_refresh.py      ✅ final consistent token refresher
│   ├── device_loader.py      ✅ final consistent YAML loader
├── config/
│   ├── secrets.yaml          ✅ your secret keys
│   ├── tuya_devices.yaml     ✅ your device list
│   ├── tuya_token.json       ✅ always updated here
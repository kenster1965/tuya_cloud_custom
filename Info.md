
tuya_devices.yaml

Field in YAML	Purpose
ha_name	        HA entity ID (should be unique)
tuya_device_id	Device ID for Tuya API (used in commands)
friendly_name	User-facing name for cards/entities
dps[].id	    Data Point (DP) ID for Tuya commands
dps[].code	    DP code name (human-readable)
dps[].platform	HA platform type: sensor, switch, etc.
enabled	Whether to include the device/dp

explain that code is what is used, not so much dp id numbers

explaine about integer: true

list a few device classes:
temperature	    Temperature sensor	    °C / °F
humidity	    Relative humidity	    %
battery	        Battery level	        %
voltage	        Electrical voltage	    V
current	        Electrical current	    A
power	        Power usage     	    W
energy	        Total energy consumed	kWh / Wh
signal_strength	Signal strength (e.g. WiFi, Zigbee)	dBm
pressure	    Air pressure	        hPa / mbar
illuminance	    Light level	    lx
carbon_monoxide	CO concentration (boolean: detected or not)	—
carbon_dioxide	CO₂ level	            ppm
pm25	        Particulate matter (PM2.5)	µg/m³
pm10	        Particulate matter (PM10)	µg/m³
aqi	            Air Quality Index	index
monetary	    Currency value (e.g. cost of energy)	$ / €
timestamp	    Time value (ISO date/time string)	    —


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




This means in climate.py you can:

Attribute	From YAML
unique_id	unique_id
current temp	current_temperature_code & current_temperature_dp
target temp	target_temperature_code & target_temperature_dp
hvac_mode	hvac_modes_code & hvac_modes_dp
hvac_modes	hvac_modes dict
min_temp	min_temp
max_temp	max_temp
precision	precision
temperature_unit	temperature_unit
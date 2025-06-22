

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



| HA `HVACMode` | Meaning                           |
| ------------- | --------------------------------- |
| `off`         | System is off                     |
| `heat`        | Heat mode                         |
| `cool`        | Cool mode                         |
| `heat_cool`   | Auto (heat or cool automatically) |
| `auto`        | Fully automatic                   |
| `dry`         | Dry / Dehumidify                  |
| `fan_only`    | Fan only                          |



Field	Meaning
temp_convert	"c_to_f" → raw DP is C, convert to F before showing
"f_to_c" → raw DP is F, convert to C
If missing → no conversion, use raw
No more temperature_unit	The display unit is inferred from the temp_convert value

- climate:
    on_off:        # ✅ Optional switch for OFF
      code: switch
      type: boolean

    hvac_mode:     # ✅ Always present: Tuya mode DP
      code: mode
      dp: '2'
      type: enum
      modes:       # ✅ Explicit HA → Tuya map
        heat: 'manual'
        heat_cool: 'auto'



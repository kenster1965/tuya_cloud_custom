
# 📑 Tuya Cloud Custom — YAML Configuration Guide

## 📖 Welcome!

Welcome to the **Tuya Cloud Custom** configuration guide!
This document explains **how to write robust, flexible YAML files** to fully control how your Tuya devices appear in **Home Assistant** — your way.

---

## 🔑 secrets.yaml — Tuya Cloud API Credentials
Your Tuya Cloud Custom integration requires a secrets.yaml file in your Home Assistant /config directory. This file securely stores your Tuya Cloud API credentials and connection settings.

### ✅ Required Fields
| Field           | Required | Description                                                                                           |
| --------------- | -------- | ----------------------------------------------------------------------------------------------------- |
| `client_id`     | ✅        | Tuya IoT project Client ID.                                                                           |
| `client_secret` | ✅        | Tuya IoT project Client Secret.                                                                       |
| `base_url`      | ✅        | Tuya API region URL — e.g. `https://openapi.tuyaus.com` (US), `https://openapi.tuyaeu.com` (EU), etc. |
| `token_refresh` | ✅        | How often to refresh the access token (in minutes). **Recommended: 110 minutes**.                     |

### 📝 Optional Fields
| Field          | Required | Description                                               |
| -------------- | -------- | --------------------------------------------------------- |
| `Name`         | optional | Friendly name for your project (for your reference only). |
| `username`     | optional | Your Tuya IoT account email or phone number (optional).   |
| `password`     | optional | Your Tuya IoT account password (optional).                |
| `user_id`      | optional | Tuya Cloud user ID (optional).                            |
| `project_code` | optional | Your project identifier (optional).                       |

### 📂 Example secrets.yaml
```yaml
Name: "Ken's Custom Cloud Tuya"
client_id: "YOUR_CLIENT_ID"
client_secret: "YOUR_CLIENT_SECRET"
base_url: "https://openapi.tuyaus.com"
token_refresh: 110  # Recommended default

# Optional extras for your own reference
username: "you@example.com"
password: "YOUR_PASSWORD"
user_id: "YOUR_USER_ID"
project_code: "YOUR_PROJECT_CODE"
```

> 💡 **Pro Tip:** Store your `secrets.yaml` outside version control to stay secure. Keep it private.

---

## 📌 Top-Level Structure

Each YAML file defines **one or more entities for a single Tuya device**.

✅ **Supported entity types (so far):**
- **device** (optional metadata)
- **climate** (thermostats)
- **switch** (Yep on and off)
- **sensor** (All types including binary)
- **number** (When your wanting a slide bar or sorts)

You can mix multiple entities in the same YAML to represent all functions of a physical Tuya device.

---

## 1️⃣ Device Block
| Field | Required | Description |
|-------|----------|-----------------------------|
| `friendly_name` | ✅ | Human-friendly display name for HA's Device page. |
| `enabled` | ✅ | Enable or disable the device in HA. Keeps from getting added. |
| `tuya_device_id` | ✅ | Your Tuya Cloud device ID. This guarantees a unique stable backend ID and pins your entity IDs. |
| `tuya_product_id` | optional | Tuya Product ID. Used to build the HA model info. |
| `tuya_category` | optional | Tuya device type (e.g., `wk`, `znrb`). Used as the HA "model". |
| `local_ip` | optional | Reference only, not used. |
| `local_key` | optional |  Reference only, not used.  |
| `poll_interval` | optional | How often to poll status (seconds). Defaults to 60. |
| `version` | optional | Version info for your own tracking. |

💡 **Important:** Your tuya_device_id must be unique across all files — the loader checks for duplicates and fails setup if found.

---

## 2️⃣ Entity Blocks (Sensor, Switch, Number, Binary, Select, -adding more soon-)
| Field | Used in | Required | Description |
|-------|---------|----------|-----------------------------|
| `enabled` | All | ✅ | Enable or disable this entity. |
| `code` | All | ✅ | Tuya DP code. |
| `dp`  | All | optional | DP ID, for reference only |
| `type` | All | ✅ | Type of DP: boolean, integer, float, enum, |
| `category` | All | optional | HA `entity_category`: `config` or `diagnostic`. |
| `class` | All | optional | HA `device_class` (e.g. `temperature`, `battery`). |
| `unit_of_measurement` | Sensor, NNumberu | optional | Example: `%`, `°C`. |
| `translated` | Sensor | optional | Map raw DP → friendly labels. |
| `icon` | 	All	| optional	| Override the default UI icon. Use any Material Design Icon (MDI) code — for example, mdi:fan, mdi:thermometer, mdi:volume-high, etc. |
| `min_value`| Number | ✅ | Minimum value |
| `max_value`| Number | ✅ | Maximum value |
| `step_size`| Number | ✅ | Increment |
| `on_value` | Binary | ✅ | What value means ON, Ie true, 1, 'motion', ... |
| `options` | Select | ✅ | Map of key: label pairs. Key = sent to Tuya; label = shown in HA. |
| `is_passive_entity` | All except sensors | optional | Prevents sending commands to Tuya (HA display only). Default: false. |
| `restore_on_reconnect` | Switch, Number	| optional |	When true, Home Assistant will re-send the last known state (if HA previously set it) after a reconnect or restart. Skipped for passive entities. Defaults to false. |

### Note for restore_on_reconnect
- Does not restore state if is_passive_entity: true.
- Only restores values that HA explicitly sent before (not values received from Tuya or defaults).
- Helps keep device state consistent across reboots, power cycles, or network reconnects.
Sample:
```yaml
- switch:
    code: pump
    type: boolean
    enabled: true
    restore_on_reconnect: true
```
- This will automatically turn the pump back ON at HA startup if HA turned it on before and the device is reachable.


## 3️⃣ Climate Block — Flexible & Robust
A Climate Block Defines a thermostat entity.

| Field                 | Required | Description |
| --------------------- | -------- | --------------------------------- |
| `unique_id`           | ✅ | Globally unique ID for the thermostat. This pins both the backend ID and the UI display name. |
| `enabled`             | ✅ | Enable/disable this entity |
| `temp_convert`        | optional | Auto-convert raw temps: `"c_to_f"` or `"f_to_c"` or leave empty for no conversion. |
| `scale`	              | optional | Scale factor for raw DP. Use 10 for tenths (default) or 1 for whole degrees. |
| `current_temperature` | ✅ | DP info for current temp |
| `target_temperature`  | optional | DP info for setpoint; omit to disable |
| `on_off`              | optional | DP info for a switch to turn the climate OFF, if not part of `mode`|
| `hvac_mode`           | ✅ | Defines the DP for operating modes and maps Tuya modes to HA modes |

🔹 current_temperature / target_temperature
| Field       | Required               | Description          |
| ----------- | ---------------------- | -------------------- |
| `code`      | ✅ | Tuya DP code |
| `dp`        | optional | DP ID, for reference only |
| `type`      | ✅ | `integer` or `float` |
| `min_temp`  | optional (target only) | Minimum allowed      |
| `max_temp`  | optional (target only) | Maximum allowed      |
| `precision` | optional (target only) | Step increment       |

🔹 on_off
| Field  | Required | Description         |
| ------ | -------- | ------------------- |
| `code` | ✅ | Tuya switch DP code |
| `dp`   | optional | DP ID, for reference only |
| `type` | ✅ | `boolean` |

🔹 hvac_mode
| Field   | Required | Description                                       |
| ------- | -------- | ------------------------------------------------- |
| `code`  | ✅ | Tuya mode DP code |
| `dp`    | optional | DP ID, for reference only |
| `type`  | ✅ | `enum` |
| `modes` | ✅ | Map of `HA_mode: Tuya_mode` (e.g. `heat: manual`) |

`scale` field explained:
| Value | When to use |
| -------------- |  ------------ |
| `10` (default) | If your DP reports temperature in tenths of a degree (common for thermostats). Example: raw `820` = `82.0°F`. |
| `1` | If your DP reports whole degrees directly (common for pool heat pumps or simple thermostats). Example: raw `82` = `82°F`. |

✅ `temp_convert` handles raw C → HA F.
✅ `on_off` switch overrides mode to `OFF`.
✅ `modes` maps HA UI modes to Tuya’s values.

### Example with temperature conversion, switch, mode mapping:
```yaml
- climate:
    unique_id: upstairs_thermostat
    enabled: true
    temp_convert: "c_to_f"
    scale: 10   # raw is tenths of °C / or omomit this line
    current_temperature:
      code: temp_current
      dp: '24'
      type: integer
    target_temperature:
      code: temp_set
      dp: '16'
      type: integer
      min_temp: 40
      max_temp: 90
      precision: 1
    on_off:
      code: switch
      dp: '1'
      type: boolean
    hvac_mode:
      code: mode
      dp: '2'
      type: enum
      modes:
        heat: 'manual'
        # heat_cool: 'auto'  # Omiting so HA does not list it as a Mode
```
### Excample with same scale
```yaml
- climate:
    unique_id: pool_thermostat
    enabled: true
    scale: 1   # DP is whole degrees!
    current_temperature:
      code: temp_current_f
      dp: '35'
      type: integer
    target_temperature:
      code: set_temp59_104
      dp: '196'
      type: integer
      min_temp: 59
      max_temp: 104
      precision: 1
    on_off:
      code: switch
      dp: '1'
      type: boolean
    hvac_mode:
      code: work_mode
      dp: '5'
      type: enum
      modes:
        heat: '1'
        cool: '0'
```

## 4️⃣ Select Block
Examples of `select` block
```yaml
- select:
    code: sensor_mode
    type: enum
    options:
      in: Internal
      out: External
    enabled: true
```
```yaml
- select:
    code: fan_speed
    type: enum
    options:
      low: Low
      medium: Medium
      high: High
    enabled: true
```
HA shows:  Low | Medium | High
Sends raw:  "low", "medium", "high" to Tuya.

---

## 5️⃣ Translated Example

Map raw states to friendly labels — works for `enum`, `bitfield`, or `integer` values.
Note: at times keys like 0, 1, .. are not integers but are treated as strings so the key would then have to be in 'quotes'.

```yaml
- sensor:
    code: valve_state
    id: '36'
    type: enum
    translated:
      open: 'Heating'
      close: 'Off'
    enabled: true
```
```yaml
- sensor:
    code: fault
    id: '15'
    type: enum
    translated:
      '0': 'OK'
      '1': 'Water Off!'
    category: diagnostic
    enabled: true
```

---

## 6️⃣ How IDs Work
| What                          | How it’s built                                                               |
| ----------------------------- | ---------------------------------------------------------------------------- |
| **Device Registry ID**        | always `tuya_device_id`                                                      |
| **Device display name in UI** | `friendly_name`                                                              |
| **Entity ID pattern**         | `<platform>.<slug(friendly_name)>_<slug(code)>` (for sensor, switch, number) |
| **Climate Entity ID**         | `<platform>.<slug(friendly_name)>_<slug(unique_id)>`                         |

✅ This means:
The tuya_device_id pins your backend & avoids collisions.
The friendly_name gives a pretty display — it does not affect the ID stability.
Duplicate tuya_device_id = setup error → logged clearly.

---

## 7️⃣ Best Practices
✅ One YAML per real Tuya device — do not duplicate tuya_device_id!
✅ Use friendly_name for UI clarity — safe to rename in HA if needed.
✅ Keep code unique per entity.
✅ Use translated for friendly states.

---

## 8 Full Example YAML
```yaml
- device:
    friendly_name: Pool Heater
    tuya_device_id: abcd1234efgh5678
    tuya_category: wk
    poll_interval: 60
    version: 1
    enabled: true
- climate:
    unique_id: pool_heater
    enabled: true
    temp_convert: "c_to_f"
    current_temperature:
      code: temp_current
      dp: '24'
      type: integer
    target_temperature:
      code: temp_set
      dp: '16'
      type: integer
      min_temp: 50
      max_temp: 104
      precision: 1
    on_off:
      code: switch
      dp: '1'
      type: boolean
    hvac_mode:
      code: mode
      dp: '2'
      type: enum
      modes:
        heat: 'manual'
        heat_cool: 'auto'
- sensor:
    code: valve_state
    id: '36'
    type: enum
    translated:
      open: 'Heating'
      close: 'Idle'
    enabled: true
- sensor:
    code: battery_percentage
    id: '35'
    type: integer
    category: diagnostic
    class: battery
    unit_of_measurement: '%'
    enabled: true
```

### Info:
## `category` (Entity Category)
| Value | Meaning |
|-------|---------|
| `config` | Control or configuration entity (shows in Controls of UI). |
| `diagnostic` | Diagnostic info only (shows in Diagnostics of UI). |

## `class` (Device Class)
| Common examples |
|-----------------|
| `temperature` |
| `humidity` |
| `battery` |
| `voltage` |
| `current` |
| `power` |
| `pressure` |
| `energy` |

---

## ✅ Everything clear, flexible & future-proof!

Keep YAML clean, reload safely — **and take full control of Tuya Cloud in HA!** 🚀

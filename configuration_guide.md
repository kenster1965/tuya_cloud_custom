
# 📑 Tuya Cloud Custom — YAML Configuration Guide

## 📖 Welcome!

Welcome to the **Tuya Cloud Custom** configuration guide!
This document explains **how to write robust, flexible YAML files** to fully control how your Tuya devices appear in **Home Assistant** — your way.

---

## 📌 Top-Level Structure

Each YAML file defines **one or more entities for a single Tuya device**.

✅ **Supported entity types (so far):**
- **device** (optional metadata)
- **climate** (thermostats)
- **switch**
- **sensor**
- **number**

You can mix multiple entities in the same YAML to represent all functions of a physical Tuya device.

---

## ✅ 1️⃣ Device Block
| Field | Required | Description |
|-------|----------|-----------------------------|
| `friendly_name` | ✅ | Your custom name for HA's Device tab. |
| `enabled` | ✅ | Enable or disable the device in HA. Keeps from getting added. |
| `tuya_device_id` | ✅ | Your Tuya Cloud device ID. |
| `tuya_category` | ✅ | Tuya device type (e.g., `wk`, `znrb`). Used as the HA "model". |
| `local_ip` | optional | Reference only, not used. |
| `local_key` | optional |  Reference only, not used.  |
| `poll_interval` | optional | How often to poll status (seconds). Defaults to 60. |
| `version` | optional | Version info for your own tracking. |

---

## ✅ 2️⃣ Entity Blocks (Sensor, Switch, Number, -adding more soon-)
Legend:
Se = Sensor
Sw = Switch
Nu = Number

| Field | Used in | Required | Description |
|-------|---------|----------|-----------------------------|
| `enabled` | All | ✅ | Enable or disable this entity. |
| `code` | All | ✅ | Tuya DP code. |
| `dp`  | All | optional | DP ID, for reference only |
| `type` | All | ✅ | Type of DP: boolean, integer, float, enum, |
| `category` | All | optional | HA `entity_category`: `config` or `diagnostic`. |
| `class` | All | optional | HA `device_class` (e.g. `temperature`, `battery`). |
| `unit_of_measurement` | Se, Nu | optional | Example: `%`, `°C`. |
| `translated` | Se | optional | Map raw DP → friendly labels. |
| `min_value`| Nu | ✅ | Minimum value |
| `max_value`| Nu | ✅ | Maximum value |
| `step_size`| Nu | ✅ | Increment |


## ✅ 3️⃣ Climate Block — Flexible & Robust

✅ Climate Block
Defines a thermostat entity.
| Field                 | Required | Description |
| --------------------- | -------- | --------------------------------- |
| `unique_id`           | ✅ | Unique Home Assistant ID |
| `enabled`             | ✅ | Enable/disable this entity |
| `temp_convert`        | optional | Auto-convert raw temps: `"c_to_f"` or `"f_to_c"` |
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




Example with temperature conversion, switch, mode mapping:

```yaml
- climate:
    unique_id: upstairs_thermostat
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

✅ `temp_convert` handles raw C → HA F.
✅ `on_off` switch overrides mode to `OFF`.
✅ `modes` maps HA UI modes to Tuya’s values.

---

## ✅ 4️⃣ Translated Example

Map raw states to friendly labels — works for `enum`, `bitfield`, or `integer` values.

```yaml
- sensor:
    code: valve_state
    id: '36'
    type: enum
    translated:
      open: 'Heating'
      close: 'Off'
    enabled: true

- sensor:
    code: fault
    id: '15'
    type: bitfield
    translated:
      0: 'OK'
      1: 'Water Off!'
    category: diagnostic
    enabled: true
```

---

## ✅ 5️⃣ Key Valid Values

### `category` (Entity Category)

| Value | Meaning |
|-------|---------|
| `config` | Control or configuration entity (shows in Controls of UI). |
| `diagnostic` | Diagnostic info only (shows in Diagnostics of UI). |

### `class` (Device Class)

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

For `sensor` use, see Home Assistant’s `VALID_SENSOR_CLASSES`.

---

## ✅ 6️⃣ Best Practices

✅ Keep `tuya_category` only in the `device` block.
✅ Use `category` and `class` in entities only if you want HA to sort them nicely.
✅ Use `translated` for cleaner UI labels.
✅ For `climate` → keep `modes` map clear and match real Tuya values.

---

## ✅ 7️⃣ Full Example YAML

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

---

## ✅ Everything clear, flexible & future-proof!

Keep YAML clean, reload safely — **and take full control of Tuya Cloud in HA!** 🚀

# Tuya Cloud Custom for Home Assistant

**Tuya Cloud Custom** is a Home Assistant custom integration designed to work similarly to the built-in Tuya integration — but with more control and flexibility. This project gives you the power to define and customize how your Tuya devices are represented in Home Assistant using simple YAML configuration files.

Unlike the built-in integration, **Tuya Cloud Custom** allows you to:
- Customize each device’s entity configuration
- Add or exclude specific entities
- Control naming, device classes, platforms, and more
- Use partial control (e.g., diagnostic-only mode)
- Bypass limitations of the official Tuya integration
- Build 'Mirrored' sensors from the climate/thermastate, so you can have a sensor not tied to climate

---

## 🔧 Requirements

To use this integration, you must:
- Have a Tuya Developer Account
- Know your **Tuya API credentials** (`client_id`, `client_secret`, and `base_url`)
- Know your **device IDs** and **data point (DP) codes/IDs**

---

## 🌐 How to Get Your Tuya Credentials

1. Go to the Tuya IoT Platform: [https://us.iot.tuya.com](https://us.iot.tuya.com)
2. Log in with your Tuya Developer account or create one if you don’t have one.
3. Navigate to the **Cloud** section.
4. Create a new **Cloud Project** or use an existing one.
5. Enable the **"Smart Home" API** under the "API Group Authorization" tab.
6. Link your Tuya App (Smart Life or Tuya Smart) to the project:
    - Go to **Devices > Link Tuya App Account**
    - Use the QR code scanner in your Tuya mobile app under "Developer Mode"
    - Once linked, your devices will show up under **All Devices**
7. Go to the **Project Overview** to find:
    - `client_id`
    - `client_secret`
    - `base_url` (e.g., `https://openapi.tuyaus.com`)

---

## 📦 Finding Tuya Device IDs and DP (Data Points)

Once your app is linked to the Tuya Cloud Project:

1. Go to the **Device List** tab under your project.
2. Find the **device ID** (called `Device ID` or `UUID`) for the Tuya device you want to integrate.
3. Click on a device to view its **functions** and **status**.
4. The **functions tab** will list all the supported **DP codes and types** (e.g., `switch_1`, `temp_set`, `work_state`).
5. These DP codes are what you’ll use in your YAML configuration file.

**Note:** You can also use the `/v1.0/devices/{device_id}` API endpoint to retrieve live data and confirm DP values.

---

## 🧩 Ready to Configure Your Devices?

Once you have your Tuya credentials and device information, you’re ready to set up your custom devices in Home Assistant.

👉 See the [Configuration Guide](./configuration_guide.md) to create your YAML file for Tuya Cloud Custom.

---

## 🚀 Features

- Cloud-based control (via Tuya API)
- Customizable per-device and per-entity configuration
- Easy YAML format for defining devices and entities
- Diagnostic support for non-controllable DP values
- Works alongside or independently from the official Tuya integration

---

## 📁 Folder Structure

```bash
├── README.md
├── Info.md
├── __init__.py
├── binary_sensor.py
├── climate.py
├── config
│   ├── devices
│   │   ├── your devices.yaml
│   ├── secrets.yaml
│   └── tuya_token.json
├── config_flow.py
├── configuration_guide.md    <-- START HERE after setup
├── const.py
├── helpers
│   ├── device_loader.py
│   ├── helper.py
│   ├── token_refresh.py
│   └── tuya_command.py
├── manifest.json
├── number.py
├── select.py
├── sensor.py
├── status.py
└── switch.py
```


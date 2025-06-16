import appdaemon.plugins.hass.hassapi as hass
import yaml

class HAAddDevices(hass.Hass):
    def initialize(self):
        self.log("🛠️ Initializing HA Add Devices App")

        self.device_path = self.args.get("device_path", "/share/tuya_devices.yaml")
        self.log(f"📂 Config path set to: {self.device_path}")

        self.load_and_process_devices()

    def load_and_process_devices(self):
        try:
            with open(self.device_path, "r") as f:
                config_data = yaml.safe_load(f) or {}

            devices = config_data.get("devices", [])
            self.log(f"🔍 Loaded {len(devices)} devices from {self.device_path}")

            if not devices:
                self.log("⚠️ No devices found in the config file.")
                return

            self.process_devices(devices)

        except Exception as e:
            self.log(f"❌ Error loading device config: {e}", level="ERROR")

    def process_devices(self, devices):
        for device in devices:
            if not device.get("enabled", True):
                self.log(f"🚫 Skipping disabled device: {device.get('ha_name')}")
                continue

            ha_base = device.get("ha_name").replace("-", "_")  # HA does not line hyphens

            friendly_name = device.get("friendly_name", ha_base)
            dps = device.get("dps", [])
            self.log(f"⚙️ Processing device: {friendly_name} with {len(dps)} DPs")

            for dp in dps:
                if not dp.get("enabled", True):
                    self.log(f"  🚫 Skipping disabled DP: {dp.get('code')}")
                    continue
                self.create_or_update_entity(device, dp, ha_base, friendly_name)


    def create_or_update_entity(self, device, dp, ha_base_raw, device_friendly_name):
        platform = dp.get("platform", "sensor")
        dp_code = dp["code"]
        
        ha_base = ha_base_raw.replace("-", "_")  # Sanitize for valid entity_id
        entity_suffix = dp_code.lower().replace(" ", "_")
        entity_id = f"{platform}.{ha_base}_{entity_suffix}"

        attributes = {
            "friendly_name": f"{device_friendly_name} - {dp.get('friendly_name', dp_code)}",
            "device": ha_base,
            "tuya_code": dp_code,
            "dp_id": dp.get("id"),
            "platform": platform,
            "category": device.get("category"),
        }

        if "device_class" in dp:
            attributes["device_class"] = dp["device_class"]
        if "entity_category" in dp and dp["entity_category"]:
            attributes["entity_category"] = dp["entity_category"]
        if platform == "number":
            attributes["min"] = dp.get("min_value")
            attributes["max"] = dp.get("max_value")
            attributes["step"] = dp.get("step_size")
        if dp.get("is_passive_entity", False):
            attributes["passive"] = True

        try:
            self.set_state(entity_id, state="unknown", attributes=attributes)
            self.log(f"  ✅ Created/Updated {entity_id} with attributes: {attributes}")
        except Exception as e:
            self.log(f"❌ Failed to set state for {entity_id}: {e}", level="ERROR")

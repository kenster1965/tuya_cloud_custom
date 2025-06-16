import yaml
import os

def load_tuya_devices(config_dir):
    yaml_path = os.path.join(config_dir, "tuya_devices.yaml")
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    return [d for d in data.get("devices", []) if d.get("enabled", True)]

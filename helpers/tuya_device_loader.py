import yaml

def load_tuya_devices(devices_file):
    """
    Generic loader: takes a file path as argument.
    The caller (e.g., __init__.py) decides which file to pass.
    """
    with open(devices_file, "r") as f:
        data = yaml.safe_load(f)
    return [d for d in data.get("devices", []) if d.get("enabled", True)]

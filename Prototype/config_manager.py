import json
import os
import sys


def get_config_path():
    """Get the path to config.json, next to the executable or script."""
    try:
        # PyInstaller bundled
        base_path = os.path.dirname(sys.executable)
    except Exception:
        base_path = os.path.abspath(".")

    # In dev mode, use the script directory
    if not getattr(sys, 'frozen', False):
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, "config.json")


def load_config():
    """Load config from config.json. Returns dict with defaults if file doesn't exist."""
    defaults = {
        "case_root": os.path.join(os.path.expanduser("~"), "SMMPI_Cases")
    }

    config_path = get_config_path()

    if not os.path.exists(config_path):
        return defaults

    try:
        with open(config_path, "r") as f:
            loaded = json.load(f)
        # Merge with defaults so new keys are always present
        for key, value in defaults.items():
            if key not in loaded:
                loaded[key] = value
        return loaded
    except Exception as e:
        print(f"[!] Failed to load config: {e}")
        return defaults


def save_config(config):
    """Save config dict to config.json."""
    config_path = get_config_path()
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"[+] Config saved to {config_path}")
    except Exception as e:
        print(f"[!] Failed to save config: {e}")

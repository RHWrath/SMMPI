import json
from pathlib import Path

root = Path(__file__).parent
version_json_path = root / "version.json"
version_iss_path = root / "version.iss"

with version_json_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

version = data.get("version", "0.0.0")

with version_iss_path.open("w", encoding="utf-8") as f:
    f.write(f'#define MyAppVersion "{version}"\n')

print(f"[OK] version.iss generated with version {version}")
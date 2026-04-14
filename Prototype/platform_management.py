import json
import os
import subprocess
from utils import get_platforms_file, get_adb_path, debug_log

def load_platforms() -> list[dict]:
    """Load all platform configs from platforms.json."""
    platforms_file = get_platforms_file()

    if not platforms_file:
        print("[ERROR] platforms.json not found")
        return []

    print(f"[DEBUG] PLATFORMS_FILE = {platforms_file}")
    print(f"[DEBUG] File exists: {os.path.exists(platforms_file)}")
    print(f"[DEBUG] File size: {os.path.getsize(platforms_file) if os.path.exists(platforms_file) else 'N/A'}")

    with open(platforms_file, "r", encoding="utf-8-sig") as f:
        contents = f.read()

    print(f"[DEBUG] File contents: {repr(contents[:100])}")
    data = json.loads(contents)
    return data["platforms"]

def get_foreground_package() -> str | None:
    """
    Ask ADB which app is currently in the foreground.
    Returns the package name string or None if it can't be determined.
    """
    adb_path = get_adb_path()
    if not adb_path:
        print("[DEBUG] ADB not found for platform detection")
        return None

    try:
        result = subprocess.run(
            [adb_path, "shell", "dumpsys", "activity", "activities"],
            capture_output=True,
            text=True,
            timeout=12
        )

        output = result.stdout.strip()
        if not output:
            print("[DEBUG] No dumpsys output received")
            return None

        for line in output.splitlines():
            if "ResumedActivity" in line:
                for part in line.split():
                    if "/" in part and "." in part:
                        package = part.split("/")[0]
                        if "{" not in package and "}" not in package and ":" not in package:
                            print(f"[DEBUG] Foreground package detected: {package}")
                            return package

        print("[DEBUG] No ResumedActivity package found")
        return None

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"[DEBUG] Foreground package detection failed: {e}")
        return None

def get_platform_by_package(package_name: str) -> dict | None:
    """Return the platform config matching the given package name, or None."""
    platforms = load_platforms()
    for platform in platforms:
        if platform["package_name"] == package_name:
            return platform
    return None


def get_active_platform() -> dict | None:
    """
    Detect the foreground app and return its platform config.
    Returns None if the foreground app isn't a known platform,
    or if ADB detection fails.
    """
    package = get_foreground_package()
    if package is None:
        return None
    return get_platform_by_package(package)


def is_known_platform(package_name: str) -> bool:
    """Check if a package name matches any configured platform."""
    return get_platform_by_package(package_name) is not None
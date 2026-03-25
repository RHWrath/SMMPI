import json
import os
import subprocess


PLATFORMS_FILE = os.path.join(os.path.dirname(__file__), "platforms.json")


def load_platforms() -> list[dict]:
    """Load all platform configs from platforms.json."""
    with open(PLATFORMS_FILE, "r") as f:
        data = json.load(f)
    return data["platforms"]


def get_foreground_package() -> str | None:
    """
    Ask ADB which app is currently in the foreground.
    Returns the package name string or None if it can't be determined.
    """
    try:
        result = subprocess.run(
            "adb shell dumpsys activity activities | grep mResumedActivity",
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )

        output = result.stdout.strip()
        if not output:
            return None

        # Output looks like:
        # mResumedActivity: ActivityRecord{... com.snapchat.android/.app.SnapActivity ...}
        # We want the package name before the slash
        for part in output.split():
            if "/" in part and "." in part:
                package = part.split("/")[0]
                # Sanity check: package names don't contain braces or colons
                if "{" not in package and "}" not in package and ":" not in package:
                    return package

        return None

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
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

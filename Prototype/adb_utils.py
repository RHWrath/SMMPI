import subprocess
import sys


def _adb_kwargs():
    """Common subprocess kwargs for ADB commands."""
    kwargs = {'capture_output': True, 'text': True, 'timeout': 10}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def force_stop(package_name: str) -> None:
    """Force stop an app without relaunching it."""
    print(f"[+] Force stopping {package_name}...")
    subprocess.run(
        ['adb', 'shell', 'am', 'force-stop', package_name],
        **_adb_kwargs()
    )
    print(f"[+] {package_name} stopped")


def force_stop_and_relaunch(package_name: str) -> None:
    """
    Force stop an app and relaunch it via ADB.
    Uses monkey launcher so no activity name is needed.
    """
    force_stop(package_name)

    print(f"[+] Relaunching {package_name}...")
    subprocess.run(
        ['adb', 'shell', 'monkey', '-p', package_name,
         '-c', 'android.intent.category.LAUNCHER', '1'],
        **_adb_kwargs()
    )
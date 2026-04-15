import subprocess
import sys
from utils import get_adb_path

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
    adb_path = get_adb_path()
    if not adb_path:
        print("[ERROR] ADB not found for force stop / relaunch")
        return

    kwargs = {'capture_output': True, 'text': True, 'timeout': 10}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    print(f"[+] Force stopping {package_name}...")
    stop_result = subprocess.run(
        [adb_path, 'shell', 'am', 'force-stop', package_name],
        **kwargs
    )

    print(f"[DEBUG] force-stop return code: {stop_result.returncode}")
    print(f"[DEBUG] force-stop stdout: {stop_result.stdout}")
    print(f"[DEBUG] force-stop stderr: {stop_result.stderr}")

    print(f"[+] Relaunching {package_name}...")
    relaunch_result = subprocess.run(
        [adb_path, 'shell', 'monkey', '-p', package_name,
         '-c', 'android.intent.category.LAUNCHER', '1'],
        **kwargs
    )

    print(f"[DEBUG] relaunch return code: {relaunch_result.returncode}")
    print(f"[DEBUG] relaunch stdout: {relaunch_result.stdout}")
    print(f"[DEBUG] relaunch stderr: {relaunch_result.stderr}")

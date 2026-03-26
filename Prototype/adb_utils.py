import subprocess
import sys


def force_stop_and_relaunch(package_name: str) -> None:
    """
    Force stop an app and relaunch it via ADB.
    Uses monkey launcher so no activity name is needed.
    """
    kwargs = {'capture_output': True, 'text': True, 'timeout': 10}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    print(f"[+] Force stopping {package_name}...")
    subprocess.run(
        ['adb', 'shell', 'am', 'force-stop', package_name],
        **kwargs
    )

    print(f"[+] Relaunching {package_name}...")
    subprocess.run(
        ['adb', 'shell', 'monkey', '-p', package_name,
         '-c', 'android.intent.category.LAUNCHER', '1'],
        **kwargs
    )

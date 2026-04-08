import os

from ppadb.client import Client as AdbClient
import shutil
import subprocess
import sys
from tkinter import messagebox
import tkinter as tk

def start_adb_server():
    """Start ADB server if bundled or system ADB is available, otherwise show error and exit."""
    base_path = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.abspath(".")

    adb_candidates = [
        os.path.join(base_path, "platform-tools", "adb.exe"),
        os.path.join(base_path, "_internal", "platform-tools", "adb.exe"),
        shutil.which("adb")
    ]

    adb_path = next((path for path in adb_candidates if path and os.path.exists(path)), None)

    if not adb_path:
        print("[!] ADB not found (bundled or PATH)")

        root = tk.Tk()
        root.withdraw()

        messagebox.showerror(
            "ADB Required",
            "Android Debug Bridge (ADB) could not be found.\n\n"
            "The application checked:\n"
            "• platform-tools next to the application\n"
            "• _internal\\platform-tools inside the packaged app\n"
            "• the system PATH\n\n"
            "Please make sure ADB is bundled with the application or installed on the machine.\n\n"
            "The application will now close."
        )

        root.destroy()
        sys.exit(1)

    try:
        subprocess.run([adb_path, "start-server"], check=False)
        print(f"[+] ADB server started using: {adb_path}")
    except Exception as e:
        print(f"[!] Failed to start ADB server: {e}")

        root = tk.Tk()
        root.withdraw()

        messagebox.showerror(
            "ADB Start Failed",
            f"ADB was found, but the server could not be started.\n\n"
            f"Resolved path:\n{adb_path}\n\n"
            f"Error:\n{e}\n\n"
            "The application will now close."
        )

        root.destroy()
        sys.exit(1)
    
    

def select_device():
    client = AdbClient(host="127.0.0.1", port=5037)

    devices = client.devices()

    if not devices:
        return None

    while True:
        try:
            choice = int(input("Select device number: "))
            if 0 <= choice < len(devices):
                return devices[choice]
        except ValueError:
            pass
        print("Invalid selection, try again.")

def push_file(device, local_path, remote_path):
    try:
        device.push(local_path, remote_path)
    except Exception as e:
        print(f"Failed to push file: {e}")

def start_scrcpy(device):
    scrcpy_path = shutil.which("scrcpy")
    if scrcpy_path:
        try:
            subprocess.run([scrcpy_path, "-s", device.serial], check=False)
        except Exception as e:
            print(f"Failed to start scrcpy: {e}")
    else:
        print("Please install scrcpy")

def stop_scrcpy(device):
    try:
        device.shell("pkill -f scrcpy")
    except Exception as e:
        print(f"Failed to stop scrcpy: {e}")

if __name__ == "__main__":
    device = select_device()

    if device:
        print(f"\nUsing device: {device.serial}")
        print("Android version:", device.shell("getprop ro.build.version.release"))
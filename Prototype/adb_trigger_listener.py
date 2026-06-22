import subprocess
import sys
import threading
from typing import Callable, Optional

from utils import get_adb_path


class AdbTriggerListener:
    def __init__(
        self,
        device_serial: str,
        on_trigger: Callable[[str], None],
        tag: str = "ANDROID_LISTENER",
    ):
        self.device_serial = device_serial
        self.on_trigger = on_trigger
        self.tag = tag

        self.process: Optional[subprocess.Popen] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self):
        if self.running:
            print("[!] ADB trigger listener already running")
            return

        adb_path = get_adb_path()
        if not adb_path:
            raise RuntimeError("ADB executable not found")

        cmd = [
            adb_path,
            "-s", self.device_serial,
            "logcat",
            "-s", self.tag,
        ]

        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
            "text": True,
            "bufsize": 1,
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        subprocess.run(
            [adb_path, "-s", self.device_serial, "logcat", "-c"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        self.process = subprocess.Popen(cmd, **kwargs)
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

        print(f"[+] ADB trigger listener started for {self.device_serial}")

    def _read_loop(self):
        if not self.process or not self.process.stdout:
            return

        try:
            for line in self.process.stdout:
                if not self.running:
                    break

                cleaned_line = line.strip()
                if not cleaned_line:
                    continue

                print(f"[ADB LISTENER] {cleaned_line}", flush=True)

                if "AUDIO_LISTENER_EVENT type=MIC_OPEN" in cleaned_line:
                    self.on_trigger(cleaned_line)

                elif "AUDIO_LISTENER_EVENT type=MIC_CLOSED" in cleaned_line:
                    self.on_trigger(cleaned_line)

        except Exception as e:
            print(f"[ERROR] ADB trigger listener: {e}", flush=True)
        finally:
            self.running = False

    def stop(self):
        self.running = False

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self.process = None
        print("[+] ADB trigger listener stopped")

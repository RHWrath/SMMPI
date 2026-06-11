import subprocess
import threading
import time
from datetime import datetime

from utils import get_ffplay_path
APP_START = time.monotonic()

class AudioPlayer:

    def __init__(self):
        self.process = None
        self.ffplay_path = get_ffplay_path()
        self.keep_alive_process = None

        if not self.ffplay_path:
            raise FileNotFoundError("ffplay.exe could not be found.")

    def play(self, file_path, on_finished=None):
        self.stop()

        def run_player():
            self.process = subprocess.Popen(
                [
                    self.ffplay_path,
                    "-nodisp",
                    "-autoexit",
                    file_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("[AUDIO] Real audio started", flush=True)

            self.process.wait()
            self.process = None

            if on_finished:
                on_finished()


        thread = threading.Thread(target=run_player, daemon=True)
        thread.start()

    def stop(self):
        if not self.process or self.process.poll() is not None:
            return
        self.process.terminate()
        self.process = None

        print("[AUDIO] Real audio stopped", flush=True)

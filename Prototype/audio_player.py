import subprocess
import threading
import time
from datetime import datetime

from utils import get_ffplay_path
APP_START = time.monotonic()

class AudioPlayer:

    """ def debug_event(name, **data):
        elapsed = time.monotonic() - APP_START
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        details = " ".join(f"{key}={value}" for key, value in data.items())
        print(f"[{timestamp} +{elapsed:.3f}s] {name} {details}", flush=True) """

    def __init__(self):
        self.process = None
        self.ffplay_path = get_ffplay_path()

        if not self.ffplay_path:
            raise FileNotFoundError("ffplay.exe could not be found.")

    def play(self, file_path, on_finished=None):
        #self.debug_event("PLAY_REQUESTED", file=file_path)

        self.stop()
        #self.debug_event("AFTER_STOP_BEFORE_FFPLAY")

        def run_player():
            #self.debug_event("FFPLAY_POPEN_BEFORE", file=file_path)
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
            #self.debug_event("FFPLAY_POPEN_AFTER", pid=self.process.pid)


            self.process.wait()
            #self.debug_event("FFPLAY_EXITED", returncode=self.process.returncode)
            self.process = None

            if on_finished:
                #self.debug_event("ON_FINISHED_BEFORE")
                on_finished()
                #self.debug_event("ON_FINISHED_AFTER")


        thread = threading.Thread(target=run_player, daemon=True)
        thread.start()
        #self.debug_event("PLAY_THREAD_STARTED")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process = None

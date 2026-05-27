from dataclasses import dataclass
from typing import Optional, Callable
import os
from datetime import datetime
import time
import sys
import subprocess
import threading

from utils import get_ffmpeg_path


@dataclass
class RecordingSession:
    case_name: str
    output_folder: str
    temp_file_path: str
    final_file_path: str
    capture_x: int
    capture_y: int
    capture_width: int
    capture_height: int
    window_title: str
    audio_device: str | None = None
    is_recording: bool = False


class RecordingManager:
    def __init__(self):
        self.recording_process: Optional[subprocess.Popen] = None
        self.current_session: Optional[RecordingSession] = None
        self._stop_thread: Optional[threading.Thread] = None

    def is_recording(self) -> bool:
        return (
            self.recording_process is not None
            and self.recording_process.poll() is None
        )

    def is_stopping(self) -> bool:
        return self._stop_thread is not None and self._stop_thread.is_alive()

    def create_session(
        self,
        case_folder: str,
        capture_x: int,
        capture_y: int,
        capture_width: int,
        capture_height: int,
        window_title: str,
        audio_device: str | None = None,
        is_recording: bool = False
    ) -> RecordingSession:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        os.makedirs(case_folder, exist_ok=True)

        temp_file_path = os.path.join(case_folder, f"{timestamp}_temp.mkv")
        final_file_path = os.path.join(case_folder, f"{timestamp}.mp4")

        session = RecordingSession(
            case_name=os.path.basename(case_folder),
            output_folder=case_folder,
            temp_file_path=temp_file_path,
            final_file_path=final_file_path,
            capture_x=capture_x,
            capture_y=capture_y,
            capture_width=self._make_even(capture_width),
            capture_height=self._make_even(capture_height),
            window_title=window_title,
            audio_device=audio_device,
            is_recording=is_recording
        )

        self.current_session = session
        return session

    def _make_even(self, value: int) -> int:
        return value if value % 2 == 0 else value - 1

    def _sanitize_name(self, value: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        cleaned = "".join("_" if c in invalid_chars else c for c in value.strip())
        return cleaned if cleaned else "recording"

    def _get_subprocess_kwargs_for_background_process(self) -> dict:
        kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        return kwargs

    def _get_subprocess_kwargs_for_capture_process(self) -> dict:
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        return kwargs

    def start_recording(self):
        if not self.current_session:
            raise RuntimeError("No recording session has been created.")

        if self.is_recording():
            raise RuntimeError("Recording is already running.")

        if self.is_stopping():
            raise RuntimeError("Recording is currently stopping. Please wait.")

        if sys.platform != "win32":
            raise RuntimeError("Recording is currently only supported on Windows.")

        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError(
                "FFmpeg executable not found. Please ensure FFmpeg is installed and added to PATH."
            )

        session = self.current_session

        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "gdigrab",
            "-framerate", "30",
            "-i", f"title={session.window_title}",
            "-vf", f"crop@phone={session.capture_width}:{session.capture_height}:{session.capture_x}:{session.capture_y}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            session.temp_file_path
        ]

        kwargs = self._get_subprocess_kwargs_for_background_process()

        print("[REC][RM][START] start_recording() called")
        print(f"[REC][RM][START] ffmpeg_path = {ffmpeg_path}")
        print(f"[REC][RM][START] window_title = {session.window_title}")
        print(f"[REC][RM][START] temp_file_path = {session.temp_file_path}")
        print(f"[REC][RM][START] command = {' '.join(cmd)}")

        self.recording_process = subprocess.Popen(cmd, **kwargs)

        print(f"[REC][RM][START] pid = {self.recording_process.pid}")
        print(f"[REC][RM][START] immediate poll = {self.recording_process.poll()}")

        session.is_recording = True

       

    def stop_recording(self):
        """
        Synchronous stop.
        Use this only if blocking the current thread is acceptable.

        Recommended for UI:
        use stop_recording_async() instead.
        """
        if not self.is_recording():
            raise RuntimeError("No recording is currently running.")

        if not self.current_session:
            raise RuntimeError("No recording session has been created.")

        print("[REC][RM][STOP] stop_recording() called")

        session = self.current_session
        process = self.recording_process

        forced = self._stop_ffmpeg_process(process)

        session.is_recording = False
        self.recording_process = None

        self._log_temp_file_state(session.temp_file_path)

        if forced:
            raise RuntimeError(
                "Recording was force-stopped; temp file may be invalid, remux skipped."
            )

        self._validate_temp_file(session.temp_file_path)

        # Small buffer to make sure Windows releases the file handle.
        time.sleep(0.3)

        self.remux_to_mp4()

        return session.final_file_path

    def stop_recording_async(
        self,
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Stops recording in a separate thread so the UI does not freeze.

        Important:
        If you update CustomTkinter/Tkinter UI inside on_success/on_error,
        call those callbacks through app.after(...), not directly from the worker thread.
        """
        if self.is_stopping():
            raise RuntimeError("Recording is already stopping.")

        if not self.is_recording():
            raise RuntimeError("No recording is currently running.")

        self._stop_thread = threading.Thread(
            target=self._stop_recording_worker,
            args=(on_success, on_error),
            daemon=False
        )
        self._stop_thread.start()

    def _stop_recording_worker(
        self,
        on_success: Optional[Callable[[str], None]],
        on_error: Optional[Callable[[Exception], None]]
    ):
        try:
            final_file_path = self.stop_recording()

            if on_success:
                on_success(final_file_path)

        except Exception as e:
            print(f"[REC][RM][STOP][ASYNC] Stop failed: {e}")

            if on_error:
                on_error(e)

    def _stop_ffmpeg_process(self, process: Optional[subprocess.Popen]) -> bool:
        """
        Stops FFmpeg gracefully if possible.

        Returns:
            False = graceful stop succeeded
            True = process had to be terminated/killed
        """
        if not process:
            raise RuntimeError("Recording process does not exist.")

        forced = False

        try:
            if process.stdin:
                print("[REC][RM][STOP] Sending 'q' to ffmpeg stdin...")
                process.stdin.write(b"q\n")
                process.stdin.flush()

                try:
                    process.stdin.close()
                    print("[REC][RM][STOP] stdin closed")
                except Exception as e:
                    print(f"[REC][RM][STOP] stdin close failed: {e}")

        except Exception as e:
            print(f"[REC][RM][STOP] Failed to send 'q': {e}")

        try:
            print("[REC][RM][STOP] Waiting up to 10s for ffmpeg to exit gracefully...")
            process.wait(timeout=10)
            print(f"[REC][RM][STOP] ffmpeg exited gracefully with returncode={process.returncode}")

        except subprocess.TimeoutExpired:
            forced = True
            print("[REC][RM][STOP] Graceful stop timed out, terminating process...")

            process.terminate()

            try:
                process.wait(timeout=5)
                print(f"[REC][RM][STOP] ffmpeg terminated with returncode={process.returncode}")

            except subprocess.TimeoutExpired:
                print("[REC][RM][STOP] Terminate timed out, killing process...")

                process.kill()
                process.wait(timeout=5)

                print(f"[REC][RM][STOP] ffmpeg killed with returncode={process.returncode}")

        return forced

    def _log_temp_file_state(self, temp_file_path: str):
        print(f"[REC][RM][STOP] temp exists = {os.path.exists(temp_file_path)}")

        if os.path.exists(temp_file_path):
            print(f"[REC][RM][STOP] temp size = {os.path.getsize(temp_file_path)} bytes")

    def _validate_temp_file(self, temp_file_path: str):
        if not os.path.exists(temp_file_path):
            raise RuntimeError("Temporary recording file does not exist.")

        temp_size = os.path.getsize(temp_file_path)

        if temp_size <= 0:
            raise RuntimeError("Temporary recording file is empty.")

    def remux_to_mp4(self):
        if not self.current_session:
            raise RuntimeError("No recording session has been created.")

        session = self.current_session

        self.remux_file_to_mp4(
            temp_file_path=session.temp_file_path,
            final_file_path=session.final_file_path
        )

    def remux_file_to_mp4(self, temp_file_path: str, final_file_path: str):
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError(
                "FFmpeg executable not found. Please ensure FFmpeg is installed and added to PATH."
            )

        self._validate_temp_file(temp_file_path)

        cmd = [
            ffmpeg_path,
            "-y",
            "-i", temp_file_path,
            "-c", "copy",
            "-movflags", "+faststart",
            final_file_path
        ]

        print("[REC][RM][REMUX] remux_file_to_mp4() called")
        print(f"[REC][RM][REMUX] temp_file_path = {temp_file_path}")
        print(f"[REC][RM][REMUX] final_file_path = {final_file_path}")
        print(f"[REC][RM][REMUX] command = {' '.join(cmd)}")

        kwargs = self._get_subprocess_kwargs_for_capture_process()

        result = subprocess.run(cmd, **kwargs)

        print(f"[REC][RM][REMUX] returncode = {result.returncode}")
        print(f"[REC][RM][REMUX] stdout = {result.stdout}")
        print(f"[REC][RM][REMUX] stderr = {result.stderr}")

        if result.returncode != 0:
            raise RuntimeError(f"Failed to remux MKV to MP4: {result.stderr}")

        if not os.path.exists(final_file_path):
            raise RuntimeError("Remux finished but final MP4 file was not created.")

        if os.path.getsize(final_file_path) <= 0:
            raise RuntimeError("Remux finished but final MP4 file is empty.")

        print(f"[REC][RM][REMUX] final size = {os.path.getsize(final_file_path)} bytes")

    def recover_temp_recordings(self, case_folder: str) -> list[str]:
        """
        Searches for unfinished *_temp.mkv files and tries to convert them to MP4.

        Use this on app startup or when opening a case folder.
        """
        recovered_files = []

        if not os.path.exists(case_folder):
            print(f"[REC][RM][RECOVERY] case_folder does not exist: {case_folder}")
            return recovered_files

        print(f"[REC][RM][RECOVERY] Checking folder: {case_folder}")

        for filename in os.listdir(case_folder):
            if not filename.endswith("_temp.mkv"):
                continue

            temp_file_path = os.path.join(case_folder, filename)
            final_filename = filename.replace("_temp.mkv", ".mp4")
            final_file_path = os.path.join(case_folder, final_filename)

            if os.path.exists(final_file_path) and os.path.getsize(final_file_path) > 0:
                print(f"[REC][RM][RECOVERY] Already recovered, skipping: {final_file_path}")
                continue

            try:
                print(f"[REC][RM][RECOVERY] Unfinished recording found: {temp_file_path}")

                self._validate_temp_file(temp_file_path)

                self.remux_file_to_mp4(
                    temp_file_path=temp_file_path,
                    final_file_path=final_file_path
                )

                recovered_files.append(final_file_path)

                print(f"[REC][RM][RECOVERY] Recovered: {final_file_path}")

            except Exception as e:
                print(f"[REC][RM][RECOVERY] Failed to recover {temp_file_path}: {e}")

        return recovered_files

    def cleanup_temp_file(self):
        """
        Optional cleanup.
        Only call this after successful remux if you do not want to keep the MKV.
        For evidence safety, I would not delete automatically yet.
        """
        if not self.current_session:
            return

        temp_file_path = self.current_session.temp_file_path

        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"[REC][RM][CLEANUP] Deleted temp file: {temp_file_path}")
            except Exception as e:
                print(f"[REC][RM][CLEANUP] Failed to delete temp file: {e}")
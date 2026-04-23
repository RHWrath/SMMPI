from dataclasses import dataclass
from typing import Optional
import os
from datetime import datetime
import sys
import subprocess
from utils import get_ffmpeg_path


@dataclass
class RecordingSession:
    case_name: str
    platform_name: str
    output_folder: str
    temp_file_path: str
    final_file_path: str
    capture_x: int
    capture_y: int
    capture_width: int
    capture_height: int
    audio_device: str | None = None
    is_recording: bool = False
    
class RecordingManager:
    def __init__(self):
        self.recording_process = None
        self.current_session: Optional[RecordingSession] = None
        
    def is_recording(self) -> bool:
        return self.recording_process is not None and self.recording_process.poll() is None
    
    def create_session(
        self,
        case_folder: str,
        platform_name: str,
        capture_x: int,
        capture_y: int,
        capture_width: int,
        capture_height: int,
        audio_device: str | None = None
    ) -> RecordingSession:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_platform_name = self._sanitize_name(platform_name)

        temp_file_path = os.path.join(case_folder, f"{safe_platform_name}_{timestamp}_temp.mkv")
        final_file_path = os.path.join(case_folder, f"{safe_platform_name}_{timestamp}.mp4")

        session = RecordingSession(
            case_name=os.path.basename(case_folder),
            platform_name=platform_name,
            output_folder=case_folder,
            temp_file_path=temp_file_path,
            final_file_path=final_file_path,
            capture_x=capture_x,
            capture_y=capture_y,
            capture_width=capture_width,
            capture_height=capture_height,
            audio_device=audio_device,
            is_recording=False
        )

        self.current_session = session
        return session
    
    
    def __sanitize_name(self, value: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        cleaned = "".join(c for c in invalid_chars if c not in value.strip())
        return cleaned if cleaned else "recording"
    
    def start_recording (self): 
        if not self.current_session:
            raise RuntimeError("No recording session has been created")
        
        if self.is_recording():
            raise RuntimeError("Recording is already running.")
        
        if sys.platform != "win32": 
            raise RuntimeError("Recording is currently only supported on Windows.")
        
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg executable not found. Please ensure FFmpeg is installed and added to PATH.")
                
        session = self.current_session
        
        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "gdigrab",
            "-framerate", "30",
            "-offset_x", str(session.capture_x),
            "-offset_y", str(session.capture_y),
            "-video_size", f"{session.capture_width}x{session.capture_height}",
            "-i", "desktop",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            session.temp_file_path
        ]        
        
        kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,        
            }
        
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            
        self.recording_process = subprocess.Popen(cmd, **kwargs)
        session.is_recording = True    
        
    def stop_recording(self):
        if not self.is_recording():
            raise RuntimeError("No recording is currently running.")
        
        try: 
            if self.recording_process.stdin:
                self.recording_process.stdin.write(b"q\n")
                self.recording_process.stdin.flush()
        except Exception:
            pass
        
        try: 
            self.recording_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.recording_process.terminate()
            try:
                self.recording_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.recording_process.kill()
                self.recording_process.wait(timeout=5)
                
        if self.current_session:
            self.current_session.is_recording = False
            
        self.recording_process = None        
            
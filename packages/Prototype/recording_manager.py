from dataclasses import dataclass
import socket
from typing import Optional
import os
from datetime import datetime
import time
import sys
import subprocess
from utils import get_ffmpeg_path
import zmq

def ffmpeg_supports_zmq(ffmpeg_path: str) -> bool:
    try:
        result = subprocess.run(
            [ffmpeg_path, "-filters"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=10
        )

        if result.returncode != 0:
            return False

        output = result.stdout.lower()
        return " zmq " in output or "\n... zmq " in output or "azmq" in output
    except Exception:
        return False

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
    window_title: str
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
        window_title: str,  
        audio_device: str | None = None,
        is_recording: bool = False
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
            capture_width=self._make_even(capture_width),
            capture_height=self._make_even(capture_height),
            window_title=window_title,
            audio_device=audio_device,
            is_recording=False
        )

        self.current_session = session
        return session
    
    def _make_even(self, value: int) -> int:
        return value if value % 2 == 0 else value - 1

    
    def _sanitize_name(self, value: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        cleaned = "".join("_" if c in invalid_chars else c for c in value.strip())
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
                
   
        self.zmq_port = self._get_free_port()
        if not self.zmq_port:
            raise RuntimeError("Failed to find a free port for ZMQ communication.")
   
        session = self.current_session
        
        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "gdigrab",
            "-framerate", "30",
            "-i", f"title={session.window_title}",
           "-vf", (
                f"zmq=bind_address=tcp\\\\://127.0.0.1\\\\:{self.zmq_port},"
                f"crop@phone={session.capture_width}:{session.capture_height}:{session.capture_x}:{session.capture_y}"),
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
        
        print("[REC][RM][START] start_recording() called")
        print(f"[REC][RM][START] ffmpeg_path = {ffmpeg_path}")
        print(f"[REC][RM][START] window_title = {session.window_title}")
        print(f"[REC][RM][START] temp_file_path = {session.temp_file_path}")
        print(f"[REC][RM][START] command = {' '.join(cmd)}")
        
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            
        self.recording_process = subprocess.Popen(cmd, **kwargs)
        
        print(f"[REC][RM][START] pid = {self.recording_process.pid}")
        print(f"[REC][RM][START] immediate poll = {self.recording_process.poll()}")
        
        session.is_recording = True    
        
        time.sleep(0.5)
        poll_result = self.recording_process.poll()
        print(f"[REC][RM][START] poll after 500ms = {poll_result}")
        
        if poll_result is not None:
            stdout, stderr = self.recording_process.communicate()
            print(f"[REC][RM][START] stdout = {stdout}")
            print(f"[REC][RM][START] stderr = {stderr}")
            
    def stop_recording(self):
        if not self.is_recording():
            raise RuntimeError("No recording is currently running.")

        print("[REC][RM][STOP] stop_recording() called")

        try:
            if self.recording_process.stdin:
                print("[REC][RM][STOP] Sending 'q' to ffmpeg stdin...")
                self.recording_process.stdin.write(b"q\n")
                self.recording_process.stdin.flush()
                try:
                    self.recording_process.stdin.close()
                    print("[REC][RM][STOP] stdin closed")
                except Exception as e:
                    print(f"[REC][RM][STOP] stdin close failed: {e}")
        except Exception as e:
            print(f"[REC][RM][STOP] Failed to send 'q': {e}")

        forced = False

        try:
            print("[REC][RM][STOP] Waiting up to 10s for ffmpeg to exit gracefully...")
            self.recording_process.wait(timeout=10)
            print(f"[REC][RM][STOP] ffmpeg exited gracefully with returncode={self.recording_process.returncode}")
        except subprocess.TimeoutExpired:
            forced = True
            print("[REC][RM][STOP] Graceful stop timed out, terminating process...")
            self.recording_process.terminate()
            try:
                self.recording_process.wait(timeout=5)
                print(f"[REC][RM][STOP] ffmpeg terminated with returncode={self.recording_process.returncode}")
            except subprocess.TimeoutExpired:
                print("[REC][RM][STOP] Terminate timed out, killing process...")
                self.recording_process.kill()
                self.recording_process.wait(timeout=5)
                print(f"[REC][RM][STOP] ffmpeg killed with returncode={self.recording_process.returncode}")

        if self.current_session:
            self.current_session.is_recording = False

        rc = self.recording_process.returncode if self.recording_process else None
        self.recording_process = None

        if not self.current_session:
            return

        temp_path = self.current_session.temp_file_path
        print(f"[REC][RM][STOP] temp exists = {os.path.exists(temp_path)}")
        if os.path.exists(temp_path):
            print(f"[REC][RM][STOP] temp size = {os.path.getsize(temp_path)} bytes")

        # Ha force stop volt, ne remuxolj rögtön
        if forced:
            raise RuntimeError("Recording was force-stopped; temp file may be invalid, remux skipped.")

        # kis puffer, hogy a file release biztos meglegyen
        time.sleep(0.3)

        self.remux_to_mp4()
                
            
            
    def remux_to_mp4(self):
        if not self.current_session:
            raise RuntimeError("No recording session has been created")

        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg executable not found. Please ensure FFmpeg is installed and added to PATH.")

        session = self.current_session

        cmd = [
            ffmpeg_path,
            "-y",
            "-i", session.temp_file_path,
            "-c", "copy",
            "-movflags", "+faststart",
            session.final_file_path
        ]

        print("[REC][RM][REMUX] remux_to_mp4() called")
        print(f"[REC][RM][REMUX] temp_file_path = {session.temp_file_path}")
        print(f"[REC][RM][REMUX] final_file_path = {session.final_file_path}")
        print(f"[REC][RM][REMUX] command = {' '.join(cmd)}")

        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(cmd, **kwargs)

        print(f"[REC][RM][REMUX] returncode = {result.returncode}")
        print(f"[REC][RM][REMUX] stdout = {result.stdout}")
        print(f"[REC][RM][REMUX] stderr = {result.stderr}")

        if result.returncode != 0:
            raise RuntimeError("Failed to remux MKV to MP4.")     
        
        
    def update_crop(self, x: int, y: int, width: int, height: int):
        if not self.is_recording():
            return
        
        context = None
        socket = None
        
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 1000)
            socket.setsockopt(zmq.SNDTIMEO, 1000)
            
            socket.connect(f"tcp://127.0.0.1:{self.zmq_port}")
            
            commands = [
            f"crop@phone x {x}",
            f"crop@phone y {y}",
            f"crop@phone w {width}",
            f"crop@phone h {height}",
         ]

            for command in commands:
                print(f"[DEBUG] Sending crop command: {command}")
                socket.send_string(command)
                reply = socket.recv_string()
                print(f"[DEBUG] ZMQ reply: {reply}")
                
            if self.current_session:
                self.current_session.capture_x = x
                self.current_session.capture_y = y
                self.current_session.capture_width = width
                self.current_session.capture_height = height
        
        except Exception as e:
            print(f"[ERROR] Failed to update crop: {e}")
            
        finally:
            if socket is not None:
                socket.close()
            if context is not None:
                context.term()    
                
    def _get_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
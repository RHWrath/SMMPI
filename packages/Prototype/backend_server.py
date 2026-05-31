import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from queue import Empty, Queue

from adb_utils import force_stop, force_stop_and_relaunch
from platform_management import get_active_platform, load_platforms
from session import Session
from utils import get_adb_path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}


def start_adb_server():
    adb = get_adb_path()
    if not adb:
        raise RuntimeError("ADB executable not found")
    subprocess.run(
        [adb, "start-server"],
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def stop_adb_server():
    adb = get_adb_path()
    if not adb:
        return
    subprocess.run(
        [adb, "kill-server"],
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


class BackendState:
    def __init__(self):
        self.control_conn = None
        self.control_lock = threading.Lock()
        self.frame_conn = None
        self.frame_lock = threading.Lock()
        self.selected_device = None
        self.session = None
        self.stream = None
        self.stream_thread = None
        self.stream_frames = Queue(maxsize=1)
        self.stream_pump_thread = None
        self.running = True
        self.recording = None

    def send(self, message):
        data = json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self.control_lock:
            if self.control_conn:
                self.control_conn.sendall(data.encode("utf-8"))

    def event(self, name, **payload):
        self.send({"type": "event", "event": name, **payload})

    def reply(self, request_id, ok=True, **payload):
        self.send({"type": "response", "id": request_id, "ok": ok, **payload})

    def error(self, request_id, message):
        self.reply(request_id, ok=False, error=str(message))


def _device_info(device):
    try:
        model = device.shell("getprop ro.product.model").strip()
        manufacturer = device.shell("getprop ro.product.manufacturer").strip()
        android = device.shell("getprop ro.build.version.release").strip()
    except Exception:
        model = "Unknown"
        manufacturer = "Unknown"
        android = ""

    return {
        "serial": device.serial,
        "manufacturer": manufacturer,
        "model": model,
        "androidVersion": android,
        "displayName": f"{manufacturer} {model}".strip() or device.serial,
        "state": "connected",
    }


class AdbDeviceAdapter:
    def __init__(self, serial):
        self.serial = serial

    def shell(self, command):
        adb = get_adb_path()
        if not adb:
            raise RuntimeError("ADB executable not found")
        result = subprocess.run(
            [adb, "-s", self.serial, "shell", command],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"ADB shell failed: {command}")
        return result.stdout

    def push(self, local_path, remote_path):
        adb = get_adb_path()
        if not adb:
            raise RuntimeError("ADB executable not found")
        result = subprocess.run(
            [adb, "-s", self.serial, "push", local_path, remote_path],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"ADB push failed: {remote_path}")


def _list_devices():
    adb = get_adb_path()
    if not adb:
        raise RuntimeError("ADB executable not found")
    result = subprocess.run(
        [adb, "devices"],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Could not list ADB devices")

    devices = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(AdbDeviceAdapter(parts[0]))
    return devices


def _media_type(path):
    ext = os.path.splitext(path.lower())[1]
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def _scan_media(folder):
    items = []
    if not folder or not os.path.isdir(folder):
        return items

    for root, _, files in os.walk(folder):
        for name in files:
            path = os.path.join(root, name)
            kind = _media_type(path)
            if kind != "unknown":
                items.append({"path": path, "fileName": name, "type": kind})
    items.sort(key=lambda item: item["fileName"].lower())
    return items


def _send_image(state, path, platform):
    from image_to_video import convert_image_to_video, resize_image_to_phone_camera, trigger_media_scan

    if not state.selected_device:
        raise RuntimeError("No device selected")

    photo_mode = platform.get("photo_mode", "vcam")
    if photo_mode == "gallery":
        photo_config = platform["photo"]
        gallery_path = platform["gallery_path"]
        filename = photo_config.get("filename", "virtual_photo.jpg")
        remote_path = f"{gallery_path}{filename}"

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_path = tmp.name

        try:
            ok = resize_image_to_phone_camera(
                path,
                temp_path,
                target_width=photo_config["width"],
                target_height=photo_config["height"],
                rotate=photo_config.get("rotate"),
                mirror=photo_config.get("mirror"),
                resize_mode=photo_config.get("resize_mode", "fill"),
            )
            if not ok:
                raise RuntimeError("Failed to resize image")
            state.selected_device.push(temp_path, remote_path)
            trigger_media_scan(state.selected_device, remote_path)
            return f"Image pushed to gallery for {platform['name']}"
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    video_config = platform["video"]
    remote_folder = platform["remote_folder"]
    filename = video_config.get("filename", "virtual.mp4")
    remote_path = f"{remote_folder}{filename}"

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        temp_path = tmp.name

    try:
        ok = convert_image_to_video(
            path,
            temp_path,
            duration=10,
            target_width=video_config["width"],
            target_height=video_config["height"],
            rotate=video_config.get("rotate"),
            mirror=video_config.get("mirror"),
            resize_mode=video_config.get("resize_mode", "fill"),
        )
        if not ok:
            raise RuntimeError("Failed to convert image to video")
        state.selected_device.push(temp_path, remote_path)
        force_stop_and_relaunch(platform["package_name"])
        return f"Image converted and pushed to {platform['name']}"
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _send_video(state, path, platform):
    from video import convert_video, get_video_duration

    if not state.selected_device:
        raise RuntimeError("No device selected")

    video_config = platform["video"]
    max_duration = video_config.get("max_duration", 60)
    duration = get_video_duration(path)
    if duration > max_duration:
        raise RuntimeError(f"Video too long ({duration:.1f}s). Max is {max_duration}s.")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        temp_path = tmp.name

    try:
        ok = convert_video(path, temp_path, video_config, max_duration=max_duration)
        if not ok:
            raise RuntimeError("Failed to convert video")
        remote_path = f"{platform['remote_folder']}virtual.mp4"
        state.selected_device.push(temp_path, remote_path)
        force_stop_and_relaunch(platform["package_name"])
        return f"Video pushed to {platform['name']} ({duration:.1f}s)"
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _encode_frame(frame):
    import cv2

    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        return None
    height, width = frame.shape[:2]
    return width, height, encoded.tobytes()


def _send_frame(state, width, height, payload):
    meta = json.dumps(
        {"width": width, "height": height, "format": "jpeg", "timestamp": time.time()},
        separators=(",", ":"),
    ).encode("utf-8")
    packet = struct.pack(">I", len(meta)) + meta + struct.pack(">I", len(payload)) + payload
    with state.frame_lock:
        if state.frame_conn:
            state.frame_conn.sendall(packet)


def _stream_display_loop(state):
    timeout = time.time() + 15
    while state.running and state.stream and state.stream.running and state.stream.width is None and time.time() < timeout:
        time.sleep(0.05)

    if not state.stream or state.stream.width is None:
        state.event("stream_status", status="error", message="No frames received")
        return

    state.event("stream_status", status="running", width=state.stream.width, height=state.stream.height)
    while state.running and state.stream and state.stream.running:
        try:
            frame = state.stream.frame_queue.get(timeout=0.1)
            if state.stream_frames.full():
                try:
                    state.stream_frames.get_nowait()
                except Empty:
                    pass
            state.stream_frames.put_nowait(frame)
        except Empty:
            pass
        except Exception as exc:
            state.event("stream_status", status="error", message=str(exc))
            break


def _frame_pump_loop(state):
    while state.running:
        try:
            frame = state.stream_frames.get(timeout=0.1)
        except Empty:
            continue
        try:
            encoded = _encode_frame(frame)
            if encoded is not None:
                _send_frame(state, *encoded)
        except Exception as exc:
            state.event("stream_status", status="error", message=f"Frame encode failed: {exc}")


def _start_stream(state, max_size=1080, max_fps=60):
    if state.stream:
        return

    from stream_new import ScrcpyStream

    state.stream = ScrcpyStream(max_size=max_size, max_fps=max_fps)
    state.stream.display_frames = lambda: _stream_display_loop(state)
    state.stream_thread = threading.Thread(target=state.stream.run, daemon=True)
    state.stream_thread.start()
    if not state.stream_pump_thread or not state.stream_pump_thread.is_alive():
        state.stream_pump_thread = threading.Thread(target=_frame_pump_loop, args=(state,), daemon=True)
        state.stream_pump_thread.start()
    state.event("stream_status", status="starting")


def _stop_stream(state):
    if state.stream:
        state.stream.running = False
        try:
            state.stream.cleanup()
        except Exception:
            pass
    state.stream = None
    state.event("stream_status", status="stopped")


def handle_command(state, command):
    request_id = command.get("id")
    name = command.get("command")
    args = command.get("args") or {}

    try:
        if name == "shutdown":
            state.reply(request_id)
            state.running = False
            return

        if name == "start_adb":
            start_adb_server()
            state.reply(request_id)
            return

        if name == "stop_adb":
            stop_adb_server()
            state.reply(request_id)
            return

        if name == "list_devices":
            devices = _list_devices()
            state.reply(request_id, devices=[_device_info(device) for device in devices])
            return

        if name == "select_device":
            serial = args.get("serial")
            for device in _list_devices():
                if device.serial == serial:
                    state.selected_device = device
                    os.environ["ANDROID_SERIAL"] = serial
                    state.reply(request_id, device=_device_info(device))
                    return
            raise RuntimeError(f"Device not found: {serial}")

        if name == "start_session":
            session = Session(args["officerName"], args["caseNumber"], args["caseRoot"])
            session.ensure_case_folder()
            state.session = session
            state.reply(
                request_id,
                session={
                    "officerName": session.officer_name,
                    "caseNumber": session.case_number,
                    "caseRoot": session.case_root,
                    "casePath": session.case_path,
                    "evidencePath": session.get_evidence_path(),
                },
            )
            return

        if name == "list_cases":
            case_root = args["caseRoot"]
            cases = []
            if os.path.isdir(case_root):
                for entry in sorted(os.listdir(case_root)):
                    path = os.path.join(case_root, entry)
                    if os.path.isdir(path):
                        cases.append({"caseNumber": entry, "fileCount": len(os.listdir(path))})
            state.reply(request_id, cases=cases)
            return

        if name == "scan_media":
            state.reply(request_id, items=_scan_media(args["folder"]))
            return

        if name == "platforms":
            state.reply(request_id, platforms=load_platforms())
            return

        if name == "active_platform":
            platform = get_active_platform()
            state.reply(request_id, platform=platform)
            return

        if name == "send_media":
            path = args["path"]
            platform = get_active_platform()
            if platform is None:
                raise RuntimeError("No supported platform detected in foreground")
            kind = _media_type(path)
            message = _send_image(state, path, platform) if kind == "image" else _send_video(state, path, platform)
            state.reply(request_id, message=message, platform=platform)
            return

        if name == "close_foreground_app":
            platform = get_active_platform()
            if platform is None:
                raise RuntimeError("No supported platform detected in foreground")
            force_stop(platform["package_name"])
            state.reply(request_id, message=f"{platform['name']} closed", platform=platform)
            return

        if name == "start_stream":
            _start_stream(state, args.get("maxSize", 1080), args.get("maxFps", 60))
            state.reply(request_id)
            return

        if name == "stop_stream":
            _stop_stream(state)
            state.reply(request_id)
            return

        if name == "touch":
            if not state.stream:
                return state.reply(request_id)
            state.stream.send_touch_event(args["action"], int(args["x"]), int(args["y"]))
            state.reply(request_id)
            return

        if name == "keycode":
            if state.stream:
                state.stream.send_keycode(int(args["keyCode"]), int(args.get("action", 0)))
            state.reply(request_id)
            return

        if name == "text":
            if state.stream:
                state.stream.send_text(args.get("text", ""))
            state.reply(request_id)
            return

        if name == "start_recording":
            from recording_manager import RecordingManager

            case_folder = args.get("caseFolder")
            officer_name = args.get("officerName")
            case_number = args.get("caseNumber")
            case_root = args.get("caseRoot")
            if state.session:
                case_folder = state.session.case_path
            elif officer_name and case_number and case_root:
                session = Session(officer_name, case_number, case_root)
                session.ensure_case_folder()
                state.session = session
                case_folder = session.case_path
            elif not case_folder:
                case_folder = os.path.join(os.path.expanduser("~"), "Desktop")

            os.makedirs(case_folder, exist_ok=True)
            if state.recording is None:
                state.recording = RecordingManager()
            platform = get_active_platform() or {"name": "UnknownPlatform"}
            state.recording.create_session(
                case_folder=case_folder,
                platform_name=platform["name"],
                capture_x=int(args["x"]),
                capture_y=int(args["y"]),
                capture_width=int(args["width"]),
                capture_height=int(args["height"]),
                window_title=args["windowTitle"],
                audio_device=args.get("audioDevice"),
            )
            state.recording.start_recording()
            state.reply(request_id, platform=platform, isRecording=True, caseFolder=case_folder)
            return

        if name == "stop_recording":
            if state.recording is None:
                raise RuntimeError("No recording is currently running.")
            state.recording.stop_recording()
            path = state.recording.current_session.final_file_path if state.recording.current_session else None
            state.reply(request_id, isRecording=False, path=path)
            return

        if name == "update_recording_crop":
            if state.recording is not None:
                state.recording.update_crop(int(args["x"]), int(args["y"]), int(args["width"]), int(args["height"]))
            state.reply(request_id)
            return

        raise RuntimeError(f"Unknown command: {name}")
    except Exception as exc:
        state.error(request_id, exc)


def serve(control_listener, frame_listener):
    state = BackendState()

    print(
        json.dumps(
            {
                "type": "ready",
                "control_port": control_listener.getsockname()[1],
                "frame_port": frame_listener.getsockname()[1],
            }
        ),
        flush=True,
    )

    state.control_conn, _ = control_listener.accept()
    state.frame_conn, _ = frame_listener.accept()
    state.event("backend_status", status="connected")

    with state.control_conn.makefile("r", encoding="utf-8") as reader:
        while state.running:
            line = reader.readline()
            if not line:
                break
            try:
                handle_command(state, json.loads(line))
            except json.JSONDecodeError as exc:
                state.event("backend_status", status="error", message=str(exc))

    _stop_stream(state)
    try:
        if state.recording is not None and state.recording.is_recording():
            state.recording.stop_recording()
    except Exception:
        pass
    try:
        stop_adb_server()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-port", type=int, default=0)
    parser.add_argument("--frame-port", type=int, default=0)
    args = parser.parse_args()

    control_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    control_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    control_listener.bind(("127.0.0.1", args.control_port))
    control_listener.listen(1)

    frame_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    frame_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    frame_listener.bind(("127.0.0.1", args.frame_port))
    frame_listener.listen(1)

    serve(control_listener, frame_listener)


if __name__ == "__main__":
    main()

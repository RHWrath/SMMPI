import os
import sys
import shutil


def get_base_path():
    """Return runtime base path for dev and bundled app."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_platforms_file():
    """Resolve platforms.json path for dev and bundled app."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "platforms.json"),
        os.path.join(base_path, "_internal", "platforms.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "platforms.json"),
    ]

    for path in candidates:
        if os.path.exists(path):
            print(f"[DEBUG] Found platforms.json at: {path}")
            return path

    return None

def get_adb_path():
    """Resolve adb from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "platform-tools", "adb.exe"),
        os.path.join(base_path, "_internal", "platform-tools", "adb.exe"),
        shutil.which("adb"),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    return None


def get_scrcpy_server_path():
    """Resolve scrcpy from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path,  "scrcpy-server-v3.3.4"),
        os.path.join(base_path, "_internal", "scrcpy-server-v3.3.4"),
        shutil.which("scrcpy-server-v3.3.4"), 
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    return None

def get_ffmpeg_path():
    """Resolve ffmpeg from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "ffmpeg" , "ffmpeg.exe"),
        os.path.join(base_path, "_internal", "ffmpeg",  "ffmpeg.exe"),
        shutil.which("ffmpeg"),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    return None


def get_ffprobe_path():
    """Resolve ffprobe from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "ffmpeg" , "ffprobe.exe"),
        os.path.join(base_path, "_internal", "ffmpeg",  "ffprobe.exe"),
        shutil.which("ffprobe"),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    return None


def debug_log(message: str):
    try:
        if getattr(sys, 'frozen', False):
            # EXE esetén az exe mellé logol
            base_path = os.path.dirname(sys.executable)
        else:
            # dev módban a projekt gyökérbe
            base_path = os.path.dirname(os.path.abspath(__file__))

        log_path = os.path.join(base_path, "debug_log.txt")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    except Exception:
        pass
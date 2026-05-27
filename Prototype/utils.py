import os
import sys
import shutil
import json


def get_base_path():
    """Return runtime base path for dev and bundled app."""
    if getattr(sys, "frozen", False):
        path = os.path.dirname(sys.executable)
        print(f"[PATH][BASE] Running as bundled EXE")
        print(f"[PATH][BASE] sys.executable = {sys.executable}")
        print(f"[PATH][BASE] Base path resolved to: {path}")
        return path

    path = os.path.dirname(os.path.abspath(__file__))
    print(f"[PATH][BASE] Running in development mode")
    print(f"[PATH][BASE] __file__ = {__file__}")
    print(f"[PATH][BASE] Base path resolved to: {path}")
    return path


def get_platforms_file():
    """Resolve platforms.json path for dev and bundled app."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "platforms.json"),
        os.path.join(base_path, "_internal", "platforms.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "platforms.json"),
    ]

    print("\n[SEARCH][PLATFORMS] Searching for platforms.json...")

    for path in candidates:
        print(f"[SEARCH][PLATFORMS] Checking: {path}")

        if os.path.exists(path):
            print(f"[FOUND][PLATFORMS] Found platforms.json at: {path}")
            return path

    print("[ERROR][PLATFORMS] platforms.json could not be found")
    return None


def get_adb_path():
    """Resolve adb from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "platform-tools", "adb.exe"),
        os.path.join(base_path, "_internal", "platform-tools", "adb.exe"),
        shutil.which("adb"),
    ]

    print("\n[SEARCH][ADB] Searching for adb.exe...")

    for path in candidates:
        print(f"[SEARCH][ADB] Checking: {path}")

        if path and os.path.exists(path):
            print(f"[FOUND][ADB] adb.exe found at: {path}")
            return path

    print("[ERROR][ADB] adb.exe could not be resolved")
    return None


def get_scrcpy_server_path():
    """Resolve scrcpy from bundled locations."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "scrcpy-server-v3.3.4"),
        os.path.join(base_path, "_internal", "scrcpy-server-v3.3.4"),
    ]

    print("\n[SEARCH][SCRCPY] Searching for scrcpy server...")

    for path in candidates:
        print(f"[SEARCH][SCRCPY] Checking: {path}")

        if path and os.path.exists(path):
            print(f"[FOUND][SCRCPY] scrcpy server found at: {path}")
            return path

    print("[ERROR][SCRCPY] scrcpy server could not be resolved")
    return None


def get_ffmpeg_path():
    """Resolve ffmpeg from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "ffmpeg", "ffmpeg.exe"),
        os.path.join(base_path, "_internal", "ffmpeg", "ffmpeg.exe"),
        shutil.which("ffmpeg"),
    ]

    print("\n[SEARCH][FFMPEG] Searching for ffmpeg.exe...")

    for path in candidates:
        print(f"[SEARCH][FFMPEG] Checking: {path}")

        if path and os.path.exists(path):
            print(f"[FOUND][FFMPEG] ffmpeg.exe found at: {path}")
            return path

    print("[ERROR][FFMPEG] ffmpeg.exe could not be resolved")
    return None


def get_ffprobe_path():
    """Resolve ffprobe from bundled locations first, then PATH."""
    base_path = get_base_path()

    candidates = [
        os.path.join(base_path, "ffmpeg", "ffprobe.exe"),
        os.path.join(base_path, "_internal", "ffmpeg", "ffprobe.exe"),
        shutil.which("ffprobe"),
    ]

    print("\n[SEARCH][FFPROBE] Searching for ffprobe.exe...")

    for path in candidates:
        print(f"[SEARCH][FFPROBE] Checking: {path}")

        if path and os.path.exists(path):
            print(f"[FOUND][FFPROBE] ffprobe.exe found at: {path}")
            return path

    print("[ERROR][FFPROBE] ffprobe.exe could not be resolved")
    return None


def debug_log(message: str):
    try:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        log_path = os.path.join(base_path, "debug_log.txt")

        print(f"[DEBUG_LOG] Writing log to: {log_path}")
        print(f"[DEBUG_LOG] Message: {message}")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    except Exception as e:
        print(f"[DEBUG_LOG][ERROR] Failed to write debug log: {e}")
        
        

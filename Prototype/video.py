import subprocess
import tempfile
import os
import sys
from utils import get_ffmpeg_path, get_ffprobe_path


def get_video_duration(video_path):
    try:
        ffprobe_path = get_ffprobe_path()
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        kwargs = {'capture_output': True, 'text': True, 'timeout': 10}
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(cmd, **kwargs)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return 0
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0


def convert_video(video_path, output_video_path, platform_config, max_duration=60):
    """
    Convert a video using dimensions and transforms from platform_config.
    platform_config is the video dict from platforms.json.
    """
    try:
        duration = get_video_duration(video_path)
        if duration > max_duration:
            print(f"Video duration ({duration:.1f}s) exceeds maximum ({max_duration}s)")
            return False

        print(f"Original video duration: {duration:.1f}s")

        target_width = platform_config["width"]
        target_height = platform_config["height"]
        rotate = platform_config.get("rotate")
        mirror = platform_config.get("mirror")

        filters = []

        if rotate is not None:
            # ffmpeg transpose values: 0=ccw+vflip, 1=cw, 2=ccw, 3=cw+vflip
            # We only handle -90 (ccw = transpose=2) for now
            if rotate == -90:
                filters.append("transpose=2")
            elif rotate == 90:
                filters.append("transpose=1")
            # Swap dimensions to match the rotation
            target_width, target_height = target_height, target_width

        if mirror:
            filters.append("hflip")

        filters.append(f"scale={target_width}:-1")
        filters.append(f"crop={target_width}:{target_height}")
        filters.append("fps=30")

        filter_string = ",".join(filters)
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            print("[ERROR] FFmpeg not found")
            return False

        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-vf', filter_string,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-y',
            output_video_path
        ]

        print(f"Converting video with filters: {filter_string}")

        kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': max_duration * 3
        }
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(cmd, **kwargs)

        if result.returncode != 0:
            print(f"[ERROR] FFmpeg failed: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"[ERROR] convert_video exception: {e}")
        return False


def on_video_confirm(app_instance):
    if not app_instance.current_selected_file:
        app_instance.info_label.configure(text="No file selected")
        return

    if not app_instance.selected_device:
        app_instance.info_label.configure(text="No device connected")
        return

    if not app_instance.active_platform:
        app_instance.info_label.configure(text="No supported platform detected")
        return

    try:
        from adb_setup import push_file

        platform_config = app_instance.active_platform["video"]
        platform_name = app_instance.active_platform["name"]
        remote_folder = app_instance.active_platform["remote_folder"]
        max_duration = platform_config.get("max_duration", 60)

        duration = get_video_duration(app_instance.current_selected_file)
        if duration > max_duration:
            app_instance.info_label.configure(
                text=f"Video too long ({duration:.1f}s). Max is {max_duration}s."
            )
            return

        w = platform_config["width"]
        h = platform_config["height"]

        app_instance.info_label.configure(
            text=f"Converting video ({duration:.1f}s) for {platform_name} ({w}x{h})..."
        )
        app_instance.app.update()

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video_path = temp_video.name

        success = convert_video(
            app_instance.current_selected_file,
            temp_video_path,
            platform_config,
            max_duration=max_duration
        )

        if not success:
            app_instance.info_label.configure(text="Failed to convert video")
            try:
                os.unlink(temp_video_path)
            except:
                pass
            return

        remote_path = f"{remote_folder}virtual.mp4"

        app_instance.info_label.configure(text="Pushing video to device...")
        app_instance.app.update()

        push_ok = push_file(app_instance.selected_device, temp_video_path, remote_path)

        try:
            os.unlink(temp_video_path)
        except:
            pass

        if not push_ok:
            app_instance.info_label.configure(
                text=(
                    "Failed to push video to device — check USB connection, device "
                    "authorization, and that the target app has been opened at least once"
                )
            )
            return

        app_instance.info_label.configure(text=f"Restarting {platform_name}...")
        app_instance.app.update()

        from adb_utils import force_stop_and_relaunch
        force_stop_and_relaunch(app_instance.active_platform["package_name"])

        app_instance.info_label.configure(
            text=f"Done — pushed virtual.mp4 to {platform_name} ({duration:.1f}s, {w}x{h})"
        )

    except Exception as e:
        app_instance.info_label.configure(text=f"Error: {str(e)}")
        print(f"Error in on_video_confirm: {e}")
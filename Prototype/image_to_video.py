import subprocess
import tempfile
import os
import sys
from PIL import Image


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_ffmpeg_path():
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_path):
            print(f"[DEBUG] Using imageio-ffmpeg: {ffmpeg_path}")
            return ffmpeg_path
    except ImportError:
        print("[DEBUG] imageio-ffmpeg not available, trying other methods")
    except Exception as e:
        print(f"[DEBUG] Error getting imageio-ffmpeg path: {e}")

    bundled_ffmpeg = get_resource_path("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if os.path.exists(bundled_ffmpeg):
        print(f"[DEBUG] Using bundled ffmpeg: {bundled_ffmpeg}")
        return bundled_ffmpeg

    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"[DEBUG] Using system ffmpeg: {ffmpeg}")
        return ffmpeg

    print("[ERROR] No ffmpeg found!")
    return "ffmpeg"


def get_device_resolution(device):
    try:
        output = device.shell("wm size")
        size_line = output.strip()
        if "Physical size:" in size_line:
            resolution = size_line.split("Physical size:")[-1].strip()
        else:
            resolution = size_line.split(":")[-1].strip()
        width, height = map(int, resolution.split('x'))
        return (width, height)
    except Exception as e:
        print(f"Error getting device resolution: {e}")
        return (1080, 1920)


def resize_image_to_phone_camera(image_path, output_path, platform_config):
    """
    Resize and optionally transform an image based on the platform config.
    platform_config is the photo dict from platforms.json.
    """
    target_width = platform_config["width"]
    target_height = platform_config["height"]
    rotate = platform_config.get("rotate")
    mirror = platform_config.get("mirror")

    try:
        with Image.open(image_path) as img:
            print(f"[DEBUG] Original image size: {img.width}x{img.height}")

            if rotate is not None:
                img = img.rotate(rotate, expand=True)
                # After rotation swap target dimensions to match
                target_width, target_height = target_height, target_width

            if mirror:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (0, 0, 0))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img_ratio = img.width / img.height
            target_ratio = target_width / target_height

            if img_ratio > target_ratio:
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * img_ratio)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            canvas = Image.new('RGB', (target_width, target_height), (0, 0, 0))
            paste_x = (target_width - new_width) // 2
            paste_y = (target_height - new_height) // 2
            canvas.paste(img, (paste_x, paste_y))

            canvas.save(output_path, 'JPEG', quality=95)
            print(f"[DEBUG] Image resized and saved to {output_path}")
            return True

    except Exception as e:
        print(f"[ERROR] Failed to resize image: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def convert_image_to_video(image_path, output_video_path, platform_config, duration=10):
    """
    Convert an image to a video using the dimensions from platform_config.
    platform_config is the photo dict from platforms.json.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
            temp_image_path = temp_img.name

        target_width = platform_config["width"]
        target_height = platform_config["height"]
        print(f"[DEBUG] Resizing image to {target_width}x{target_height}")

        if not resize_image_to_phone_camera(image_path, temp_image_path, platform_config):
            print("[ERROR] Failed to resize image")
            return False

        ffmpeg_path = get_ffmpeg_path()

        if not os.path.exists(ffmpeg_path):
            import shutil
            system_ffmpeg = shutil.which("ffmpeg")
            if system_ffmpeg:
                ffmpeg_path = system_ffmpeg
            else:
                print("[ERROR] FFmpeg not found")
                return False

        cmd = [
            ffmpeg_path,
            '-loop', '1',
            '-i', temp_image_path,
            '-c:v', 'libx264',
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-vf', 'fps=30',
            '-y',
            output_video_path
        ]

        print(f"[DEBUG] Running ffmpeg command: {' '.join(cmd[:4])}...")

        kwargs = {'capture_output': True, 'text': True, 'timeout': 30}
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(cmd, **kwargs)

        try:
            os.unlink(temp_image_path)
        except:
            pass

        if result.returncode != 0:
            print(f"[ERROR] FFmpeg failed with return code {result.returncode}")
            print(f"[ERROR] FFmpeg stderr: {result.stderr}")
            return False

        print(f"[DEBUG] Successfully created video at {output_video_path}")
        return True

    except subprocess.TimeoutExpired:
        print("[ERROR] FFmpeg process timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Exception during video conversion: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def on_image_confirm(app_instance):
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

        platform_config = app_instance.active_platform["photo"]
        platform_name = app_instance.active_platform["name"]
        remote_folder = app_instance.active_platform["remote_folder"]

        w = platform_config["width"]
        h = platform_config["height"]

        app_instance.info_label.configure(
            text=f"Converting image for {platform_name} ({w}x{h})..."
        )
        app_instance.app.update()

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video_path = temp_video.name

        success = convert_image_to_video(
            app_instance.current_selected_file,
            temp_video_path,
            platform_config,
            duration=10
        )

        if not success:
            app_instance.info_label.configure(text="Failed to convert image to video")
            try:
                os.unlink(temp_video_path)
            except:
                pass
            return

        remote_path = f"{remote_folder}virtual.mp4"

        app_instance.info_label.configure(text="Pushing video to device...")
        app_instance.app.update()

        push_file(app_instance.selected_device, temp_video_path, remote_path)

        try:
            os.unlink(temp_video_path)
        except:
            pass

        app_instance.info_label.configure(text=f"Restarting {platform_name}...")
        app_instance.app.update()

        from adb_utils import force_stop_and_relaunch
        force_stop_and_relaunch(app_instance.active_platform["package_name"])

        app_instance.info_label.configure(
            text=f"Done — pushed virtual.mp4 to {platform_name} ({w}x{h})"
        )

    except Exception as e:
        app_instance.info_label.configure(text=f"Error: {str(e)}")
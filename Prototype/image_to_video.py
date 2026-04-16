import subprocess
import tempfile
import os
import sys
from PIL import Image
from utils import get_ffmpeg_path
from ui_setup import show_toast

def resize_image_to_phone_camera(image_path, output_path, target_width=1080, target_height=1920, rotate=None,
                                 mirror=None, resize_mode="fill"):
    """
    Resize image to target dimensions with optional rotation and mirroring.

    resize_mode controls how the image fits the target:
      - "fill":    Scale up to cover the full target, center-crop overflow. No black bars.
                   Use for VCAM where the image must fill the screen exactly.
      - "contain": Scale to fit within max bounds, keep original aspect ratio, no padding.
                   Use for gallery push where the app handles display layout.
      - "fit":     Scale to fit within target, pad with black to exact dimensions.
                   Legacy fallback, not recommended for any real platform.
    """
    try:
        with Image.open(image_path) as img:
            print(f"[DEBUG] Original image size: {img.width}x{img.height}")
            print(f"[DEBUG] Resize mode: {resize_mode}")

            # Apply rotation if specified
            if rotate is not None:
                img = img.rotate(rotate, expand=True)

            # Apply mirror if specified
            if mirror:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            # If rotation swaps orientation, swap target dimensions
            if rotate is not None and abs(rotate) in (90, 270):
                target_width, target_height = target_height, target_width

            # Convert to RGB
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

            if resize_mode == "fill":
                # Scale UP so the image fully covers the target, then center-crop.
                # No black bars — some edges get cropped if aspect ratios don't match.
                if img_ratio > target_ratio:
                    # Image is wider than target — match height, crop sides
                    new_height = target_height
                    new_width = int(target_height * img_ratio)
                else:
                    # Image is taller than target — match width, crop top/bottom
                    new_width = target_width
                    new_height = int(target_width / img_ratio)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center-crop to exact target dimensions
                crop_x = (new_width - target_width) // 2
                crop_y = (new_height - target_height) // 2
                img = img.crop((crop_x, crop_y, crop_x + target_width, crop_y + target_height))

                img.save(output_path, 'JPEG', quality=95)

            elif resize_mode == "contain":
                # Scale to fit within max bounds, keep original aspect ratio.
                # No padding, no cropping — output dimensions match the image's own ratio.
                # target_width/target_height are used as maximum bounds only.
                if img.width <= target_width and img.height <= target_height:
                    # Image already fits within bounds, just save as-is
                    img.save(output_path, 'JPEG', quality=95)
                else:
                    if img_ratio > target_ratio:
                        new_width = target_width
                        new_height = int(target_width / img_ratio)
                    else:
                        new_height = target_height
                        new_width = int(target_height * img_ratio)

                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    img.save(output_path, 'JPEG', quality=95)

            else:
                # "fit" — legacy behavior. Scale to fit, pad with black to exact dimensions.
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

            print(f"[DEBUG] Image resized ({resize_mode}) and saved to {output_path}")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to resize image: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def convert_image_to_video(image_path, output_video_path, duration=10, target_width=1080, target_height=1920,
                           rotate=None, mirror=None, resize_mode="fill"):
    """Convert a still image into a video file using ffmpeg."""
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
            temp_image_path = temp_img.name

        print(f"[DEBUG] Resizing image to {target_width}x{target_height}")
        if not resize_image_to_phone_camera(image_path, temp_image_path, target_width, target_height, rotate, mirror,
                                            resize_mode):
            print("[ERROR] Failed to resize image")
            return False

        ffmpeg_path = get_ffmpeg_path()

        if not ffmpeg_path:
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

        kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': 30
        }
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


def trigger_media_scan(device, file_path):
    """
    Tell Android to scan a file so it shows up in gallery apps.
    Uses 'am broadcast' with MEDIA_SCANNER_SCAN_FILE intent.
    """
    try:
        cmd = f'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file://{file_path}"'
        result = device.shell(cmd)
        print(f"[DEBUG] Media scan triggered for: {file_path}")
        print(f"[DEBUG] Media scan result: {result}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to trigger media scan: {e}")
        return False


def push_image_to_gallery(app_instance, platform_config):
    """
    Gallery mode: resize the image and push it directly to a gallery-visible
    folder on the device. Used when VCAM photo capture doesn't work (e.g. WhatsApp).
    """
    from adb_setup import push_file

    photo_config = platform_config["photo"]
    gallery_path = platform_config["gallery_path"]
    width = photo_config["width"]
    height = photo_config["height"]
    rotate = photo_config.get("rotate")
    mirror = photo_config.get("mirror")
    resize_mode = photo_config.get("resize_mode", "fill")
    filename = photo_config.get("filename", "virtual_photo.jpg")

    app_instance.info_label.configure(text=f"Resizing image ({resize_mode})...")
    app_instance.app.update()

    # Create temp file for resized image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
        temp_image_path = temp_img.name

    success = resize_image_to_phone_camera(
        app_instance.current_selected_file,
        temp_image_path,
        target_width=width,
        target_height=height,
        rotate=rotate,
        mirror=mirror,
        resize_mode=resize_mode
    )

    if not success:
        app_instance.info_label.configure(text="Failed to resize image")
        try:
            os.unlink(temp_image_path)
        except:
            pass
        return

    remote_path = f"{gallery_path}{filename}"

    app_instance.info_label.configure(text="Pushing image to device gallery...")
    app_instance.app.update()

    push_file(app_instance.selected_device, temp_image_path, remote_path)

    try:
        os.unlink(temp_image_path)
    except:
        pass

    # Trigger media scan so the image shows up in gallery/picker
    trigger_media_scan(app_instance.selected_device, remote_path)

    app_instance.info_label.configure(
        text=f"Image pushed to gallery. Use WhatsApp attach > Gallery to send it."
    )
    show_toast(app_instance.app, "Image sent successfully")



def push_image_as_video(app_instance, platform_config):
    """
    VCAM mode: convert image to video and push to Camera1 folder.
    Used for platforms where VCAM video capture works (e.g. Snapchat).
    """
    from adb_setup import push_file
    from adb_utils import force_stop_and_relaunch

    video_config = platform_config["video"]
    remote_folder = platform_config["remote_folder"]
    width = video_config["width"]
    height = video_config["height"]
    rotate = video_config.get("rotate")
    mirror = video_config.get("mirror")
    resize_mode = video_config.get("resize_mode", "fill")
    filename = video_config.get("filename", "virtual.mp4")

    app_instance.info_label.configure(
        text=f"Converting image to video ({width}x{height})..."
    )
    app_instance.app.update()

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
        temp_video_path = temp_video.name

    success = convert_image_to_video(
        app_instance.current_selected_file,
        temp_video_path,
        duration=10,
        target_width=width,
        target_height=height,
        rotate=rotate,
        mirror=mirror,
        resize_mode=resize_mode
    )

    if not success:
        app_instance.info_label.configure(text="Failed to convert image to video")
        try:
            os.unlink(temp_video_path)
        except:
            pass
        return

    remote_path = f"{remote_folder}{filename}"

    app_instance.info_label.configure(text="Pushing video to device...")
    app_instance.app.update()

    push_file(app_instance.selected_device, temp_video_path, remote_path)

    try:
        os.unlink(temp_video_path)
    except:
        pass

    # Restart the app so VCAM picks up the new file
    package_name = platform_config["package_name"]
    force_stop_and_relaunch(package_name)

    app_instance.info_label.configure(
        text=f"Successfully pushed {filename} ({width}x{height}) to device"
    )
    show_toast(app_instance.app, "Image sent successfully")


def on_image_confirm(app_instance):
    """
    Main entry point for image confirmation. Reads the detected platform config
    and routes to either gallery push or VCAM video conversion.
    """
    if not app_instance.current_selected_file:
        app_instance.info_label.configure(text="No file selected")
        return

    if not app_instance.selected_device:
        app_instance.info_label.configure(text="No device connected")
        return

    try:
        from platform_management import get_active_platform

        platform_config = get_active_platform()

        if platform_config is None:
            app_instance.info_label.configure(text="No supported platform detected in foreground")
            return

        photo_mode = platform_config.get("photo_mode", "vcam")
        platform_name = platform_config["name"]

        print(f"[DEBUG] Platform: {platform_name}, photo_mode: {photo_mode}")

        if photo_mode == "gallery":
            push_image_to_gallery(app_instance, platform_config)
        else:
            push_image_as_video(app_instance, platform_config)

    except Exception as e:
        app_instance.info_label.configure(text=f"Error: {str(e)}")
        print(f"[ERROR] on_image_confirm: {e}")
        import traceback
        traceback.print_exc()
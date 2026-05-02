import subprocess
import tempfile
import os
import sys
from PIL import Image


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def get_ffmpeg_path():
    """Get ffmpeg path, preferring bundled version"""
    # Try imageio-ffmpeg first (cross-platform, bundled binary)
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
    
    # Check if bundled version exists
    bundled_ffmpeg = get_resource_path("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if os.path.exists(bundled_ffmpeg):
        print(f"[DEBUG] Using bundled ffmpeg: {bundled_ffmpeg}")
        return bundled_ffmpeg
    
    # Fall back to system ffmpeg
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"[DEBUG] Using system ffmpeg: {ffmpeg}")
        return ffmpeg
    
    print("[ERROR] No ffmpeg found!")
    return "ffmpeg"  # Last resort, let it fail with clear error


def is_snapchat_path(path):
    if not path:
        return False
    return 'snapchat' in path.lower()

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
    
def resize_image_to_phone_camera(image_path, output_path, target_width=1080, target_height=1920, remote_folder=""):
    try:
        with Image.open(image_path) as img:
            print(f"[DEBUG] Original image size: {img.width}x{img.height}")
            
            is_snapchat = is_snapchat_path(remote_folder)
            if is_snapchat:
                img = img.rotate(-90, expand=True)
                img = img.transpose(Image.FLIP_TOP_BOTTOM)  # Mirror the image
                target_width, target_height = target_height, target_width
            
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

def convert_image_to_video(image_path, output_video_path, duration=10, target_width=1080, target_height=1920, remote_folder=""):
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
            temp_image_path = temp_img.name
        
        print(f"[DEBUG] Resizing image to {target_width}x{target_height}")
        if not resize_image_to_phone_camera(image_path, temp_image_path, target_width, target_height, remote_folder):
            print("[ERROR] Failed to resize image")
            return False

        ffmpeg_path = get_ffmpeg_path()
        print(f"[DEBUG] Using ffmpeg path: {ffmpeg_path}")
        
        # Verify ffmpeg exists
        if not os.path.exists(ffmpeg_path):
            print(f"[ERROR] FFmpeg not found at: {ffmpeg_path}")
            # Try to find it in system PATH
            import shutil
            system_ffmpeg = shutil.which("ffmpeg")
            if system_ffmpeg:
                ffmpeg_path = system_ffmpeg
                print(f"[DEBUG] Found system ffmpeg: {ffmpeg_path}")
            else:
                print("[ERROR] FFmpeg not found in system PATH either")
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
        
        # Windows-specific subprocess configuration
        kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': 30
        }
        
        if sys.platform == 'win32':
            # Hide console window on Windows
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, **kwargs)
        
        try:
            os.unlink(temp_image_path)
        except:
            pass
        
        if result.returncode != 0:
            print(f"[ERROR] FFmpeg failed with return code {result.returncode}")
            print(f"[ERROR] FFmpeg stderr: {result.stderr}")
            print(f"[ERROR] FFmpeg stdout: {result.stdout}")
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
    
    try:
        from adb_setup import push_file
        
        width, height = 1080, 1920
        
        app_instance.info_label.configure(text=f"Converting image to video ({width}x{height} - 9:16 aspect ratio)...")
        app_instance.app.update()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video_path = temp_video.name
        
        success = convert_image_to_video(
            app_instance.current_selected_file,
            temp_video_path,
            duration=10,
            target_width=width,
            target_height=height,
            remote_folder=app_instance.remote_folder
        )
        
        if not success:
            app_instance.info_label.configure(text="Failed to convert image to video")
            try:
                os.unlink(temp_video_path)
            except:
                pass
            return
        
        remote_path = f"{app_instance.remote_folder}/virtual.mp4"
        
        app_instance.info_label.configure(text="Pushing video to device...")
        app_instance.app.update()
        
        push_file(app_instance.selected_device, temp_video_path, remote_path)
        
        try:
            os.unlink(temp_video_path)
        except:
            pass
        
        app_instance.info_label.configure(text=f"Successfully created and pushed virtual.mp4 (1080x1920 - 9:16) to device")
        
    except Exception as e:
        app_instance.info_label.configure(text=f"Error: {str(e)}")
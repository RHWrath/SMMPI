import subprocess
import tempfile
import os
import sys


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
            return ffmpeg_path
    except (ImportError, Exception):
        pass
    
    # Check if bundled version exists
    bundled_ffmpeg = get_resource_path("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg
    
    # Fall back to system ffmpeg
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    return "ffmpeg"  # Last resort, let it fail with clear error


def get_ffprobe_path():
    """Get ffprobe path, preferring bundled version"""
    # Check if bundled version exists
    bundled_ffprobe = get_resource_path("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
    if os.path.exists(bundled_ffprobe):
        return bundled_ffprobe
    
    # Fall back to system ffprobe
    import shutil
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe
    
    return "ffprobe"  # Last resort, let it fail with clear error


def is_snapchat_path(path):
    if not path:
        return False
    return 'snapchat' in path.lower()

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

def convert_video(video_path, output_video_path, target_width=1080, target_height=1920, remote_folder="", max_duration=60):
    try:
        duration = get_video_duration(video_path)
        if duration > max_duration:
            print(f"Video duration ({duration:.1f}s) exceeds maximum ({max_duration}s)")
            return False
        
        print(f"Original video duration: {duration:.1f}s")
        
        is_snapchat = is_snapchat_path(remote_folder)
        
        filters = []
        
        if is_snapchat:
            # Rotate -90 degrees then mirror horizontally
            filters.append("transpose=2")
            filters.append("hflip")
            # Swap dimensions
            target_width, target_height = target_height, target_width
        
        # Scale to target width and crop height (actually width) to fit target dimensions
        filters.append(f"scale={target_width}:-1")
        filters.append(f"crop={target_width}:{target_height}")
        
        filters.append("fps=30")
        
        filter_string = ",".join(filters)
        
        ffmpeg_path = get_ffmpeg_path()
        
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
        
        # Windows-specific subprocess configuration
        kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': max_duration * 3
        }
        
        if sys.platform == 'win32':
            # Hide console window on Windows
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, **kwargs)
        
        if result.returncode != 0:
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        return False

def on_video_confirm(app_instance):
    if not app_instance.current_selected_file:
        app_instance.info_label.configure(text="No file selected")
        return
    
    if not app_instance.selected_device:
        app_instance.info_label.configure(text="No device connected")
        return
    
    try:
        from adb_setup import push_file
        
        duration = get_video_duration(app_instance.current_selected_file)
        if duration > 60:
            app_instance.info_label.configure(text=f"Video too long ({duration:.1f}s). Maximum is 60 seconds.")
            return
        
        width, height = 1080, 1920
        
        app_instance.info_label.configure(text=f"Converting video ({duration:.1f}s) to {width}x{height}...")
        app_instance.app.update()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video_path = temp_video.name
        
        success = convert_video(
            app_instance.current_selected_file,
            temp_video_path,
            target_width=width,
            target_height=height,
            remote_folder=app_instance.remote_folder,
            max_duration=60
        )
        
        if not success:
            app_instance.info_label.configure(text="Failed to convert video")
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
        
        app_instance.info_label.configure(text=f"Successfully pushed virtual.mp4 ({duration:.1f}s, {width}x{height}) to device")
        
    except Exception as e:
        app_instance.info_label.configure(text=f"Error: {str(e)}")
        print(f"Error in on_video_confirm: {e}")

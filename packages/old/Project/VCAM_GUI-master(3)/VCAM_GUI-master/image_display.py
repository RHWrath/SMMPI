import customtkinter as ctk
from PIL import Image
import os
import sys
import subprocess
import tempfile


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


class ImageDisplay:
    def __init__(self, parent_scroll_frame):
        self.scroll_frame = parent_scroll_frame
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif',
            '.bmp', '.webp', '.tiff', '.tif'
        }
        self.video_extensions = {
            '.mp4', '.mov', '.avi', '.mkv', 
            '.webm', '.flv', '.wmv', '.m4v'
        }
        self.columns = 2
        self.thumbnail_size = 250

        self._image_cache = []

    def clear_display(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self._image_cache.clear()

    def display_media_files(self, media_files, on_click_callback=None):
        self.clear_display()

        container_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        container_frame.pack(fill="both", expand=True, padx=5, pady=5)

        for col in range(self.columns):
            container_frame.grid_columnconfigure(col, weight=1, uniform="column")

        for index, file_path in enumerate(media_files):
            row = index // self.columns
            col = index % self.columns

            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()

            media_frame = ctk.CTkFrame(container_frame)
            media_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

            if ext in self.image_extensions:
                self._create_image_display(
                    media_frame, file_path, filename, on_click_callback
                )
            elif ext in self.video_extensions:
                self._create_video_display(
                    media_frame, file_path, filename, on_click_callback
                )
            else:
                self._create_video_placeholder(
                    media_frame, file_path, filename, on_click_callback
                )

    def _create_image_display(self, parent_frame, file_path, filename, on_click_callback):
        try:
            pil_image = Image.open(file_path)

            max_size = self.thumbnail_size
            ratio = min(max_size / pil_image.width, max_size / pil_image.height)

            new_width = int(pil_image.width * ratio)
            new_height = int(pil_image.height * ratio)

            pil_image = pil_image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(new_width, new_height)
            )

            image_button = ctk.CTkButton(
                parent_frame,
                image=ctk_image,
                text="",
                command=lambda: on_click_callback(file_path) if on_click_callback else None,
                fg_color="transparent",
                hover_color="#404040",
                width=self.thumbnail_size,
                height=self.thumbnail_size
            )
            image_button.pack(pady=(10, 5))

            image_button.image = ctk_image
            self._image_cache.append(ctk_image)

            filename_label = ctk.CTkLabel(
                parent_frame,
                text=filename[:20] + "..." if len(filename) > 20 else filename,
                font=("Arial", 9),
                wraplength=self.thumbnail_size - 10
            )
            filename_label.pack(pady=(0, 10))

        except Exception:
            self._create_error_placeholder(parent_frame, filename)

    def _extract_video_thumbnail(self, video_path):
        """
        Extract a thumbnail from a video file using ffmpeg.
        
        Args:
            video_path (str): Path to the video file
            
        Returns:
            PIL.Image or None: Thumbnail image or None if extraction failed
        """
        temp_thumb_path = None
        try:
            print(f"[DEBUG] Attempting to extract thumbnail from: {os.path.basename(video_path)}")
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_thumb:
                temp_thumb_path = temp_thumb.name
            
            ffmpeg_path = get_ffmpeg_path()
            
            # Extract frame at 1 second (or first frame if video is shorter)
            cmd = [
                ffmpeg_path,
                '-i', video_path,
                '-ss', '00:00:01',
                '-vframes', '1',
                '-y',
                temp_thumb_path
            ]
            
            print(f"[DEBUG] Running ffmpeg command: {' '.join(cmd[:5])}...")
            
            # Windows-specific subprocess configuration
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 5
            }
            
            if sys.platform == 'win32':
                # Hide console window on Windows
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, **kwargs)
            
            print(f"[DEBUG] FFmpeg return code: {result.returncode}")
            
            if result.returncode == 0 and os.path.exists(temp_thumb_path):
                print(f"[DEBUG] Successfully extracted thumbnail to {temp_thumb_path}")
                pil_image = Image.open(temp_thumb_path)
                pil_image.load()  # Load image data before deleting temp file
                print(f"[DEBUG] Loaded thumbnail image: {pil_image.size}")
                try:
                    os.unlink(temp_thumb_path)
                except:
                    pass
                return pil_image
            else:
                print(f"[ERROR] FFmpeg failed for {os.path.basename(video_path)}")
                if result.stderr:
                    print(f"[ERROR] FFmpeg stderr: {result.stderr[:200]}")
                if temp_thumb_path and os.path.exists(temp_thumb_path):
                    try:
                        os.unlink(temp_thumb_path)
                    except:
                        pass
                return None
                
        except Exception as e:
            print(f"[ERROR] Exception extracting video thumbnail for {os.path.basename(video_path)}: {e}")
            import traceback
            traceback.print_exc()
            if temp_thumb_path and os.path.exists(temp_thumb_path):
                try:
                    os.unlink(temp_thumb_path)
                except:
                    pass
            return None

    def _create_video_display(self, parent_frame, file_path, filename, on_click_callback):
        """Create a video thumbnail display with play icon overlay."""
        try:
            pil_image = self._extract_video_thumbnail(file_path)
            
            if pil_image is None:
                # Fall back to placeholder if thumbnail extraction failed
                self._create_video_placeholder(parent_frame, file_path, filename, on_click_callback)
                return
            
            max_size = self.thumbnail_size
            ratio = min(max_size / pil_image.width, max_size / pil_image.height)

            new_width = int(pil_image.width * ratio)
            new_height = int(pil_image.height * ratio)

            pil_image = pil_image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(new_width, new_height)
            )
            
            print(f"[DEBUG] Created CTkImage for video: {new_width}x{new_height}")

            # Use Label instead of Button for better image display
            video_label = ctk.CTkLabel(
                parent_frame,
                image=ctk_image,
                text="▶",  # Play icon
                compound="center",
                font=("Arial", 40, "bold"),
                text_color="white",
                cursor="hand2"
            )
            video_label.pack(pady=(10, 5))
            
            # Bind click event
            if on_click_callback:
                video_label.bind("<Button-1>", lambda e: on_click_callback(file_path))
            
            print(f"[DEBUG] Created video label widget for {filename}")

            video_label.image = ctk_image
            self._image_cache.append(ctk_image)

            filename_label = ctk.CTkLabel(
                parent_frame,
                text=f"🎬 {filename[:17]}..." if len(filename) > 17 else f"🎬 {filename}",
                font=("Arial", 9),
                wraplength=self.thumbnail_size - 10
            )
            filename_label.pack(pady=(0, 10))

        except Exception as e:
            print(f"Error creating video display: {e}")
            self._create_video_placeholder(parent_frame, file_path, filename, on_click_callback)

    def _create_video_placeholder(self, parent_frame, file_path, filename, on_click_callback):
        video_button = ctk.CTkButton(
            parent_frame,
            text=f"Video File\n{filename[:15]}{'...' if len(filename) > 15 else ''}\n(Video)",
            font=("Arial", 10),
            command=lambda: on_click_callback(file_path) if on_click_callback else None,
            fg_color="#2B2B2B",
            hover_color="#404040",
            width=self.thumbnail_size,
            height=self.thumbnail_size
        )
        video_button.pack(pady=10)

    def _create_error_placeholder(self, parent_frame, filename):
        error_button = ctk.CTkButton(
            parent_frame,
            text=f"Error\n{filename[:15]}{'...' if len(filename) > 15 else ''}\n(Error)",
            font=("Arial", 10),
            fg_color="#4A4A4A",
            hover_color="#404040",
            width=self.thumbnail_size,
            height=self.thumbnail_size
        )
        error_button.pack(pady=10)

    def set_columns(self, columns):
        self.columns = max(1, columns)

    def set_thumbnail_size(self, size):
        self.thumbnail_size = max(100, size)

    def display_single_image(self, parent_panel, file_path, current_display_widget=None):
        if current_display_widget:
            current_display_widget.destroy()

        ext = os.path.splitext(file_path)[1].lower()

        if ext in self.image_extensions:
            try:
                pil_image = Image.open(file_path)

                panel_width, panel_height = 300, 400
                ratio = min(panel_width / pil_image.width, panel_height / pil_image.height)

                new_width = int(pil_image.width * ratio)
                new_height = int(pil_image.height * ratio)

                pil_image = pil_image.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                )

                ctk_image = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(new_width, new_height)
                )

                image_widget = ctk.CTkLabel(
                    parent_panel,
                    image=ctk_image,
                    text=""
                )
                image_widget.pack(expand=True, pady=20)

                image_widget.image = ctk_image
                self._image_cache.append(ctk_image)

                return image_widget

            except Exception as e:
                error_widget = ctk.CTkLabel(
                    parent_panel,
                    text=f"Error loading image:\n{str(e)}",
                    font=("Arial", 12)
                )
                error_widget.pack(expand=True)
                return error_widget

        elif ext in self.video_extensions:
            try:
                pil_image = self._extract_video_thumbnail(file_path)
                
                if pil_image is None:
                    raise Exception("Could not extract video thumbnail")
                
                panel_width, panel_height = 300, 400
                ratio = min(panel_width / pil_image.width, panel_height / pil_image.height)

                new_width = int(pil_image.width * ratio)
                new_height = int(pil_image.height * ratio)

                pil_image = pil_image.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                )

                ctk_image = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(new_width, new_height)
                )

                # Container for video thumbnail with play icon
                video_container = ctk.CTkFrame(parent_panel, fg_color="transparent")
                video_container.pack(expand=True, pady=20)
                
                video_widget = ctk.CTkLabel(
                    video_container,
                    image=ctk_image,
                    text="▶",
                    compound="center",
                    font=("Arial", 60, "bold"),
                    text_color="white"
                )
                video_widget.pack()

                video_widget.image = ctk_image
                self._image_cache.append(ctk_image)
                
                # Add filename label
                filename_label = ctk.CTkLabel(
                    video_container,
                    text=f"🎬 {os.path.basename(file_path)}",
                    font=("Arial", 10)
                )
                filename_label.pack(pady=(5, 0))

                return video_container

            except Exception as e:
                error_widget = ctk.CTkLabel(
                    parent_panel,
                    text=f"Video File\n{os.path.basename(file_path)}\n\n(Thumbnail extraction failed)",
                    font=("Arial", 12)
                )
                error_widget.pack(expand=True)
                return error_widget

        else:
            video_widget = ctk.CTkLabel(
                parent_panel,
                text=(
                    f"Video File\n{os.path.basename(file_path)}\n\n"
                    "(Video preview not supported)"
                ),
                font=("Arial", 14)
            )
            video_widget.pack(expand=True)
            return video_widget

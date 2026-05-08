import customtkinter as ctk
import os
import sys
import threading

from folder_selector import FolderSelector
from image_display import ImageDisplay
from ui_setup import UISetup
from adb_setup import start_adb_server
from device_manager import DeviceManager
from stream_wrapper import ScrcpyCanvasWrapper
from image_to_video import on_image_confirm
from video import on_video_confirm


class MediaDisplayApp:
    def __init__(self):
        self.app = ctk.CTk()
        ctk.set_appearance_mode("dark")
        self.app.geometry("1400x800")
        self.app.title("ADB Media Manager")

        start_adb_server()

        self.device_manager = DeviceManager(self.app, self.on_device_selected)
        self.folder_selector = FolderSelector()
        self.image_display = None

        self.media_files = []
        self.selected_folder_path = ""
        self.current_image_display = None
        self.current_selected_file = None
        self.selected_device = None
        self.ffmpeg_process = None
        self.adb_process = None
        self.stream = None
        self.remote_folder = "/storage/emulated/0/DCIM/Camera1/"

        self.setup_ui()
        self.app.withdraw()

    def setup_ui(self):
        main_frame = UISetup.create_main_frame(self.app)

        self.left_panel, self.select_button, self.folder_path_label, self.media_scroll_frame = \
            UISetup.setup_left_panel(main_frame, self.on_folder_select)

        self.middle_panel, self.info_label = UISetup.setup_middle_panel(main_frame, self.on_media_confirm)

        (self.right_panel, self.video_canvas, self.right_status_label) = UISetup.setup_right_panel(main_frame)

        self.image_display = ImageDisplay(self.media_scroll_frame)

        self.add_device_status()

    def start_stream(self):
        if not self.selected_device:
            self.info_label.configure(text="No device connected")
            print("[!] Cannot start stream: No device selected")
            return
        if self.stream:
            self.info_label.configure(text="Stream already running")
            print("[!] Stream already running")
            return

        try:
            print(f"[+] Starting stream for device: {self.selected_device.serial}")
            self.right_status_label.configure(text="Stream has started")
            
            self.stream = ScrcpyCanvasWrapper(
                self.video_canvas,
                port=27183,
                max_size=1080,
                max_fps=24
            )
            self.stream.start()
            print("[+] Stream started in canvas")
            
            self.info_label.configure(text="Streaming started")
        except Exception as e:
            self.info_label.configure(text=f"Error: {str(e)}")
            print(f"Error starting stream: {e}")
            import traceback
            traceback.print_exc()

    def add_device_status(self):
        if self.selected_device:
            try:
                model = self.selected_device.shell("getprop ro.product.model").strip()
                manufacturer = self.selected_device.shell("getprop ro.product.manufacturer").strip()
                device_info = f"Connected: {manufacturer} {model}"
            except Exception:
                device_info = f"Connected: {self.selected_device.serial}"
        else:
            device_info = ""

        self.device_status_label = ctk.CTkLabel(
            self.right_panel,
            text=device_info,
            font=("Arial", 10),
            text_color="green" if self.selected_device else "red"
        )
        self.device_status_label.pack(pady=5)

    def on_folder_select(self):
        folder_path, self.media_files = self.folder_selector.select_folder()
        if folder_path and self.media_files:
            self.selected_folder_path = folder_path
            self.folder_path_label.configure(text=f"Path: {folder_path}")
            self.image_display.display_media_files(self.media_files, self.on_file_click)
            self.info_label.configure(text=f"Found {len(self.media_files)} media files")
        elif folder_path:
            self.selected_folder_path = folder_path
            self.folder_path_label.configure(text=f"Path: {folder_path}")
            self.info_label.configure(text="No media files found in selected folder")
        else:
            self.info_label.configure(text="No folder selected")

    def on_file_click(self, file_path):
        filename = os.path.basename(file_path)
        self.info_label.configure(text=f"Selected: {filename}")
        self.current_selected_file = file_path
        self.current_image_display = self.image_display.display_single_image(
            self.middle_panel,
            file_path,
            self.current_image_display
        )

    def on_media_confirm(self):
        """
        Handle media file confirmation - detects file type and processes accordingly.
        """
        if not self.current_selected_file:
            self.info_label.configure(text="No file selected")
            return
        
        # Get file extension to determine type
        _, ext = os.path.splitext(self.current_selected_file.lower())
        
        # Image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        # Video extensions
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
        
        if ext in image_extensions:
            print(f"Processing image file: {self.current_selected_file}")
            on_image_confirm(self)
        elif ext in video_extensions:
            print(f"Processing video file: {self.current_selected_file}")
            on_video_confirm(self)
        else:
            self.info_label.configure(text=f"Unsupported file type: {ext}")
            print(f"Unsupported file extension: {ext}")

    def on_device_selected(self, device):
        self.selected_device = device
        self.add_device_status()
        self.start_stream()

    def run(self):
        def on_close():
            if self.stream:
                self.stream.stop()
            self.app.destroy()

        self.app.protocol("WM_DELETE_WINDOW", on_close)
        self.app.after(0, self.device_manager.show_device_selection)
        self.app.mainloop()


if __name__ == "__main__":
    app = MediaDisplayApp()
    app.run()

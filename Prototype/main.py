import customtkinter as ctk
import os
import sys
import threading
import time

from folder_selector import FolderSelector
from image_display import ImageDisplay
from ui_setup import UISetup
from adb_setup import start_adb_server, stop_adb_server
from device_manager import DeviceManager
from stream_wrapper import ScrcpyCanvasWrapper
from image_to_video import on_image_confirm
from video import on_video_confirm
from platform_management import get_active_platform, is_known_platform


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
        self.active_platform = None  # set on confirm via ADB detection

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
        self.add_platform_status()

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

    def add_platform_status(self):
        self.platform_status_label = ctk.CTkLabel(
            self.right_panel,
            text="Platform: None detected",
            font=("Arial", 10),
            text_color="gray"
        )
        self.platform_status_label.pack(pady=(0, 5))

    def update_platform_status(self, platform):
        if platform:
            self.platform_status_label.configure(
                text=f"Platform: {platform['name']}",
                text_color="green"
            )
        else:
            self.platform_status_label.configure(
                text="Platform: None detected",
                text_color="red"
            )

    def detect_active_platform_with_retry(self, attempts=6, delay=1):
        """
        Try multiple times to detect the currently active platform.
        This makes detection more stable when the phone UI is in transition.
        """
        detected_platform = None
        for attempt in range(1, attempts + 1):
            detected_platform = get_active_platform()
            print(f"[Debug] Platform detection attepmt {attempt}/{attempts}: {detected_platform['name']}")            
            if detected_platform is not None:
                return detected_platform
          
            self.info_label.configure(
                text=f"Detecting platform... (attempt {attempt}/{attempts})"
            )
            self.app.update()
            time.sleep(delay)
        return None


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
        if not self.current_selected_file:
            self.info_label.configure(text="No file selected")
            return

        self.info_label.configure(
            text="Detecting active platform..."
        )
        self.app.update()

        # Detect which platform is in the foreground
        platform = self.detect_active_platform_with_retry()
        self.update_platform_status(platform)

        if platform is None:
            self.info_label.configure(text="No supported platform detected.")
            self._show_unknown_platform_popup()
            return

        self.active_platform = platform

        _, ext = os.path.splitext(self.current_selected_file.lower())

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}

        if ext in image_extensions:
            on_image_confirm(self)
        elif ext in video_extensions:
            on_video_confirm(self)
        else:
            self.info_label.configure(text=f"Unsupported file type: {ext}")

    def _show_unknown_platform_popup(self):
        popup = ctk.CTkToplevel(self.app)
        popup.title("Platform Not Recognised")
        popup.geometry("400x180")
        popup.transient(self.app)
        popup.grab_set()
        popup.geometry("+{}+{}".format(
            int(self.app.winfo_screenwidth() / 2 - 200),
            int(self.app.winfo_screenheight() / 2 - 90)
        ))

        ctk.CTkLabel(
            popup,
            text="No supported platform detected.",
            font=("Arial", 14, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            popup,
            text="Open Snapchat or WhatsApp on the phone,\nmake sure it is in the foreground,\nthen try again.",
            font=("Arial", 12)
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            popup,
            text="OK",
            width=100,
            command=popup.destroy
        ).pack()

    def on_device_selected(self, device):
        self.selected_device = device
        self.add_device_status()
        self.start_stream()

    def run(self):
        def on_close():
            if self.stream:
                self.stream.stop()
            stop_adb_server()
            self.app.destroy()

        self.app.protocol("WM_DELETE_WINDOW", on_close)
        self.app.after(0, self.device_manager.show_device_selection)
        self.app.mainloop()


if __name__ == "__main__":
    app = MediaDisplayApp()
    app.run()
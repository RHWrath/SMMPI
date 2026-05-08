import customtkinter as ctk
import os
import sys
import threading
import time

from folder_selector import FolderSelector
from image_display import ImageDisplay
from ui_setup import UISetup, show_toast
from adb_setup import start_adb_server
from ui_setup import UISetup
from adb_setup import start_adb_server, stop_adb_server
from device_manager import DeviceManager
from stream_wrapper import ScrcpyCanvasWrapper
from image_to_video import on_image_confirm
from video import on_video_confirm
from platform_management import get_active_platform
from recording_manager import RecordingManager
from case_manager import CaseManager


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

        # Connection monitoring
        self._monitor_after_id = None
        self._is_reconnecting = False

        # Session state (set during login flow)
        self.session = None
        self.setup_ui()
        self.app.withdraw()
        
        # Recording 
        self.recording_manager = RecordingManager()
        self._recording_resize_after_id = None
        self.app.bind("<Configure>", self.on_window_configure)
        self._last_sent_crop = None 
        self._recording_start_time = None
        self._recording_timer_after_id = None
       
        
    def setup_ui(self):
        main_frame = UISetup.create_main_frame(self.app)

        self.left_panel, self.select_button, self.folder_path_label, self.media_scroll_frame = \
            UISetup.setup_left_panel(main_frame, self.on_folder_select)

        self.middle_panel, self.info_label = UISetup.setup_middle_panel(main_frame, self.on_media_confirm)
        
        self.middle_panel.configure(width=360, height=460)
        self.middle_panel.pack_propagate(False) if hasattr(self.middle_panel, "pack_propagate") else None
        self.middle_panel.grid_propagate(False)

        (self.right_panel, self.video_border_frame, self.video_canvas, self.right_status_label,
         self.close_app_button, self.record_button, self.recording_timer_label) = UISetup.setup_right_panel(main_frame)

        self.record_button.configure(command=self.toggle_recording)

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
                max_fps=60
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

        if hasattr(self, 'device_status_label') and self.device_status_label.winfo_exists():
            self.device_status_label.configure(
                text=device_info,
                text_color="green" if self.selected_device else "red"
            )
        else:
            self.device_status_label = ctk.CTkLabel(
                self.right_panel,
                text=device_info,
                font=("Arial", 10),
                text_color="green" if self.selected_device else "red"
            )
            self.device_status_label.pack(pady=5)

    def add_session_status(self):
        """Add session info label to the UI after login."""
        if not self.session:
            return

        session_text = f"Officer: {self.session.officer_name}  |  Case: {self.session.case_number}"

        self.session_status_label = ctk.CTkLabel(
            self.right_panel,
            text=session_text,
            font=("Arial", 11),
            text_color="#4A9EFF"
        )
        self.session_status_label.pack(pady=(0, 5))

    def _start_connection_monitor(self):
        """Start polling the device connection every 3 seconds."""
        self._stop_connection_monitor()
        self._check_device_connection()

    def _stop_connection_monitor(self):
        """Stop the connection monitor loop."""
        if self._monitor_after_id is not None:
            self.app.after_cancel(self._monitor_after_id)
            self._monitor_after_id = None

    def _check_device_connection(self):
        """Check if the device is still reachable via ADB."""
        if self._is_reconnecting:
            return

        if self.selected_device:
            try:
                # Quick shell command to check if device responds
                self.selected_device.shell("echo ping")
            except Exception as e:
                print(f"[!] Device disconnected: {e}")
                self._handle_disconnect()
                return

        # Schedule next check
        self._monitor_after_id = self.app.after(3000, self._check_device_connection)

    def _handle_disconnect(self):
        """Clean up and prompt for reconnection."""
        self._is_reconnecting = True
        self._stop_connection_monitor()

        # Stop the stream
        if self.stream:
            try:
                self.stream.stop()
            except Exception as e:
                print(f"[!] Error stopping stream: {e}")
            self.stream = None

        # Clear device reference
        self.selected_device = None
        self.close_app_button.configure(state="disabled")

        # Update UI
        self.device_status_label.configure(
            text="Device disconnected",
            text_color="red"
        )
        self.right_status_label.configure(text="Stream stopped - device disconnected")

        show_toast(self.app, "Device disconnected - reconnect to continue", fg_color="#d94040", duration=3000)

        # Small delay so the toast is visible before the device window pops up
        self.app.after(1500, self._show_reconnect_dialog)

    def _show_reconnect_dialog(self):
        """Re-show the device selection window for reconnection."""
        self._is_reconnecting = False

        # Reset the device manager state so it doesn't carry over old selection
        self.device_manager.selected_device = None
        self.device_manager.selected_device_index = None
        self.device_manager.available_devices = []

        self.device_manager.show_device_selection()

    def add_platform_status(self):
        self.platform_status_label = ctk.CTkLabel(
            self.right_panel,
            text="Platform: None detected",
            font=("Arial", 10),
            text_color="gray"
        )
        self.platform_status_label.pack(pady=(0, 5))

    def update_platform_status(self, platform):
        if not hasattr(self, "platform_status_label") or not self.platform_status_label.winfo_exists():
            self.add_platform_status()

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
        detected_platform = None
        for attempt in range(1, attempts + 1):
            detected_platform = get_active_platform()

            name = detected_platform["name"] if detected_platform else "None"
            print(f"[Debug] Platform detection attempt {attempt}/{attempts}: {name}")

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
        """
        Handle media file confirmation - detects file type and processes accordingly.
        """
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
        self.close_app_button.configure(state="normal", command=self.close_foreground_app)
        self.start_stream()
        self._start_connection_monitor()

    def close_foreground_app(self):
        """Detect the foreground app on the device and force stop it."""
        if not self.selected_device:
            self.info_label.configure(text="No device connected")
            return

        try:
            from adb_utils import force_stop

            platform_config = get_active_platform()

            if platform_config is None:
                show_toast(self.app, "No supported platform in foreground", fg_color="#d94040")
                return

            package_name = platform_config["package_name"]
            platform_name = platform_config["name"]

            force_stop(package_name)
            show_toast(self.app, f"{platform_name} closed")
            print(f"[+] Closed {platform_name} ({package_name})")

        except Exception as e:
            show_toast(self.app, f"Failed to close app", fg_color="#d94040")
            print(f"[ERROR] close_foreground_app: {e}")

    def run(self):
        def on_close():
            self._stop_connection_monitor()
            if self.stream:
                self.stream.stop()

            # Log where evidence would be saved
            if self.session:
                print(f"[+] Session ended. Evidence path: {self.session.get_evidence_path()}")

            if self.recording_manager.is_recording():
                try:
                    self.recording_manager.stop_recording()
                except Exception as e:
                    print(f"[ERROR] Failed to stop recording on close: {e}")

            stop_adb_server()
            self.app.destroy()

        self.app.protocol("WM_DELETE_WINDOW", on_close)

        def startup_flow():
            # Step 1: Login + case selection
            case_manager = CaseManager(self.app)
            self.session = case_manager.run_login_flow()

            if not self.session:
                print("[!] Login cancelled, exiting")
                self.app.destroy()
                return

            # Show session info in the UI
            self.add_session_status()

            # Update window title with session info
            self.app.title(
                f"ADB Media Manager — {self.session.officer_name} — Case {self.session.case_number}"
            )

            # Step 2: Device selection (existing flow)
            self.device_manager.show_device_selection()

        self.app.after(0, startup_flow)
        self.app.mainloop()

    def get_widget_relative_geometry(self, widget):
        widget.update_idletasks()
        self.app.update_idletasks()

        x = widget.winfo_rootx() - self.app.winfo_rootx()
        y = widget.winfo_rooty() - self.app.winfo_rooty()
        width = widget.winfo_width()
        height = widget.winfo_height()
        
        return (x, y, width, height)
    
    
    def toggle_recording(self):
        # Stop Recoring Logic
        try:
            if self.recording_manager.is_recording():
                self.recording_manager.stop_recording()
                self.record_button.configure(text="Start Recording")
                self.info_label.configure(text="Recording stopped")
                self._last_sent_crop = None
                
                
                self.video_border_frame.configure(fg_color="black")             
                
                if self._recording_timer_after_id is not None:
                    try:
                        self.app.after_cancel(self._recording_timer_after_id)
                    except Exception:
                        pass
                    self._recording_timer_after_id = None

                self._recording_start_time = None
                self.recording_timer_label.configure(text="00:00:00", text_color="gray60")
                return
                
            if not self.session:
                self.info_label.configure(text="No active case session.")
                return
            
            platform_name = "UnknownPlatform"
            if hasattr(self, "active_platform") and self.active_platform:
                platform_name = self.active_platform["name"]
                
            x, y, w, h = self.get_widget_relative_geometry(self.video_canvas)
            self._last_sent_crop = (x, y, w, h)
            print(f"[DEBUG] Relative canvas geometry: x={x}, y={y}, w={w}, h={h}")
            print(f"[DEBUG] App root: x={self.app.winfo_rootx()}, y={self.app.winfo_rooty()}")
            print(f"[DEBUG] Canvas root: x={self.video_canvas.winfo_rootx()}, y={self.video_canvas.winfo_rooty()}")
            
            self.recording_manager.create_session(
                case_folder=self.session.case_path,
                platform_name=platform_name,
                capture_x=x,
                capture_y=y,
                capture_width=w,
                capture_height=h,
                window_title=self.app.title(),
                audio_device=None
            )    
            # Start recording Logic
            self.recording_manager.start_recording()
            self.record_button.configure(text="Stop Recording")
            self.info_label.configure(text="Recording started") 
            
            # Add red border to video canvas to indicate recording
            self.video_border_frame.configure(fg_color="red")   
            
            # Start recording timer
            self._recording_start_time = time.time()
            self.recording_timer_label.configure(text="00:00:00", text_color="red")
            self._update_recording_timer()
            
        except Exception as e:
                    self.info_label.configure(text=f"Recording error: {str(e)}")
                    print(f"[ERROR] toggle_recording: {e}")
                    
    def on_window_configure(self, event):
        if not self.recording_manager.is_recording():
            return
        if event.widget != self.app:
            return
        if self._recording_resize_after_id is not None:
            try:
                self.app.after_cancel(self._recording_resize_after_id)
            except Exception:
                pass

        self._recording_resize_after_id = self.app.after(350, self._refresh_recording_crop)

    def _refresh_recording_crop(self):
        self._recording_resize_after_id = None
        
        if not self.recording_manager.is_recording():
            return
        
        try: 
            self.app.update_idletasks()
            x, y, w, h = self.get_widget_relative_geometry(self.video_canvas)
            
            if w < 50 or h < 50:
                return

            new_crop = (x, y, w, h)
            
            if self._last_sent_crop == new_crop:
                return
            
            print(f"[DEBUG] Auto crop refresh: x={x}, y={y}, w={w}, h={h}")
            
            self.recording_manager.update_crop(x, y, w, h)
            self._last_sent_crop = new_crop        
        
        except Exception as e:
            print(f"[ERROR] Failed to refresh recording crop: {e}")
            
    def _update_recording_timer(self):
        if not self.recording_manager.is_recording():
            print(f"[DEBUG] Not updating timer - recording not active {self.recording_manager.is_recording()}")
            return
        
        elapsed = int(time.time() - self._recording_start_time)
        
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60 
        seconds = elapsed % 60

        self.recording_timer_label.configure( 
            text=f"● {hours:02d}:{minutes:02d}:{seconds:02d}",
            text_color="red"
            )
     
        self._recording_timer_after_id = self.app.after(1000, self._update_recording_timer)
            

if __name__ == "__main__":
    app = MediaDisplayApp()
    app.run()
    
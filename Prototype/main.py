from tkinter import Menu

import customtkinter as ctk
import os
import sys
import threading
import time

from folder_selector import FolderSelector
from image_display import ImageDisplay
from ui_setup import UISetup, show_toast
from adb_setup import start_adb_server, stop_adb_server
from device_manager import DeviceManager
from stream_wrapper import ScrcpyCanvasWrapper
from image_to_video import on_image_confirm
from video import on_video_confirm
from platform_management import get_active_platform
from platform_wizard import PlatformWizard, PlatformEditor
from recording_manager import RecordingManager
from case_manager import CaseManager
from about_software_manager import AboutSoftwareManager


class MediaDisplayApp:
    def __init__(self):
        self.app = ctk.CTk()
        ctk.set_appearance_mode("dark")
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
        self.remote_folder = "/storage/emulated/0/Android/data/com.snapchat.android/files/Camera1/"

        # Connection monitoring
        self._monitor_after_id = None
        self._is_reconnecting = False

        # Session state (set during login flow)
        self.session = None
        self.setup_ui()
        self.app.withdraw()
        

        # Recording
        self._ignore_configure_until = 0
        self._is_restoring_locked_geometry = False
        self.recording_manager = RecordingManager()
        self._last_sent_crop = None
        self._recording_start_time = None
        self._recording_timer_after_id = None
        self._resize_lock_geometry = None
        self._resize_warning_active = False
        self._resize_restore_after_id = None


    def setup_ui(self):

        (self.topbar, self.menu_button, self.session_toolbar_label) = UISetup.setup_topbar(self.app,
                                                                                           self.toggle_sidebar)
        (self.sidebar, self.new_case_btn, self.open_case_btn,
         self.sidebar_platform_label, self.sidebar_add_platform_btn,
         self.sidebar_manage_platforms_btn) = UISetup.setup_sidebar(
            self.app,
            self.on_new_case,
            self.on_open_case,
            self._open_add_platform_wizard,
            self._open_manage_platforms,
        )
        self.sidebar_visible = False
        
        self.about_button = ctk.CTkButton(
            self.sidebar,
            text="About",
            command=lambda: UISetup.show_about_popup(self.app)
        )
        self.about_button.pack(side="bottom", fill="x", padx=12, pady=(8, 54))
      
        # Recording
        self.recording_manager = RecordingManager()
        self._recording_resize_after_id = None
        self._recording_start_time = None
        self._recording_timer_after_id = None

        main_frame = UISetup.create_main_frame(self.app)

        self.left_panel, self.select_button, self.folder_path_label, self.media_scroll_frame = \
            UISetup.setup_left_panel(main_frame, self.on_folder_select)

        self.middle_panel, self.info_label = UISetup.setup_middle_panel(main_frame, self.on_media_confirm)

        (self.right_panel, self.video_border_frame, self.video_canvas, self.right_status_label,
         self.close_app_button, self.record_button, self.recording_timer_label) = UISetup.setup_right_panel(main_frame)

        self.record_button.configure(command=self.toggle_recording)

        self.image_display = ImageDisplay(self.media_scroll_frame)

        
        self.app.bind("<Configure>", self._on_window_configure)
        
        self.app.state("zoomed")
        
    def maximize_windowed_fullscreen(self):
        self.app.deiconify()
        self.app.update_idletasks()

        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.app.winfo_id())
                ctypes.windll.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                return
            except Exception as e:
                print(f"[WARN] Win32 maximize failed: {e}")

    def on_new_case(self):
        self.change_case(success_message="New case selected")

    def on_open_case(self):
        self.change_case(success_message="Case changed")

    def change_case(self, success_message="Case changed"):
        if not self.session:
            print("[!] Cannot change case: no active session")
            return

        if self.recording_manager.is_recording():
            show_toast(
                self.app,
                "Stop the recording before changing case",
                fg_color="#d94040",
                duration=3500
            )
            print("[!] Case change blocked: recording is currently running")
            return

        old_case = self.session.case_number

        new_session = CaseManager(self.app).select_case_for_current_officer(
            self.session.officer_name
        )

        if not new_session:
            print("[!] Case change cancelled")
            return

        self.session = new_session

        self.update_toolbar_session_label()

        self.app.title(
            f"ADB Media Manager — {self.session.officer_name} — Case {self.session.case_number}"
        )

        if hasattr(self, "session_status_label") and self.session_status_label.winfo_exists():
            self.session_status_label.configure(
                text=f"Officer: {self.session.officer_name}  |  Case: {self.session.case_number}"
            )

        if self.sidebar_visible:
            self.toggle_sidebar()

        show_toast(
            self.app,
            f"{success_message}: {self.session.case_number}",
            fg_color="#4A9EFF"
        )

        print(f"[+] Case changed from '{old_case}' to '{self.session.case_number}'")
        print(f"[+] Main app session updated to case: {self.session.case_number}")
        print(f"[+] New evidence path: {self.session.get_evidence_path()}")

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.place_forget()
            self.sidebar_visible = False
        else:
            self.sidebar.place(x=0, y=42, relheight=1.0)
            self.sidebar.lift()
            self.sidebar_visible = True
    def update_toolbar_session_label(self):
        if not hasattr(self, "session_toolbar_label"):
            return

        if self.session:
            self.session_toolbar_label.configure(
                text=f"Officer: {self.session.officer_name}  |  Case: {self.session.case_number}",
                text_color="#4A9EFF"
            )
        else:
            self.session_toolbar_label.configure(
                text="No active session",
                text_color="gray70"
            )

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
            self.right_status_label.configure(text="")

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
        """Kept as a no-op — session info is shown in the topbar only."""
        if not self.session:
            return
        session_text = f"Officer: {self.session.officer_name}  |  Case: {self.session.case_number}"
        self.session_status_label = ctk.CTkLabel(
            self.right_panel,
            text=session_text,
            font=("Arial", 11),
            text_color="#4A9EFF"
        )
        # Not packed — label kept as attribute so change_case configure calls don't crash

    def _open_add_platform_wizard(self):
        """Open the Add Platform wizard. Gated by an active session."""
        if not self.session or not self.session.officer_name:
            show_toast(self.app, "Login required to add platforms", fg_color="#d94040")
            return
        PlatformWizard(self.app, on_saved=self._on_platform_saved)

    def _open_manage_platforms(self):
        """Open the Manage Platforms editor. Gated by an active session."""
        if not self.session or not self.session.officer_name:
            show_toast(self.app, "Login required to manage platforms", fg_color="#d94040")
            return
        PlatformEditor.open(self.app, on_saved=self._on_platform_saved)

    def _on_platform_saved(self, config):
        """Hook called after the wizard or editor successfully writes."""
        print(f"[+] Platform '{config['name']}' saved by {self.session.officer_name}")

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

    def _confirm_close_while_recording(self):
        """
        Modal popup shown when the user tries to close the app while a recording
        is in progress. Returns one of:
            "stop_and_close" - stop the recording cleanly, then close
            "cancel"         - keep recording, do not close
            "force_close"    - close immediately, recording will likely be lost
        """
        popup = ctk.CTkToplevel(self.app)
        popup.title("Recording in progress")
        popup.geometry("460x260")
        popup.resizable(False, False)
        popup.transient(self.app)
        popup.grab_set()
        popup.geometry("+{}+{}".format(
            int(self.app.winfo_screenwidth() / 2 - 230),
            int(self.app.winfo_screenheight() / 2 - 130)
        ))

        # Default if the user closes the popup with the X button: keep recording
        choice = {"value": "cancel"}

        ctk.CTkLabel(
            popup,
            text="⚠  A recording is still running",
            font=("Arial", 15, "bold"),
            text_color="#d94040"
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            popup,
            text=(
                "Closing the app now can corrupt the video file.\n"
                "Stop the recording first so it can be saved properly."
            ),
            font=("Arial", 12),
            justify="center"
        ).pack(pady=(0, 18))

        button_row = ctk.CTkFrame(popup, fg_color="transparent")
        button_row.pack(pady=(0, 18))

        def pick(value):
            choice["value"] = value
            popup.destroy()

        ctk.CTkButton(
            button_row,
            text="Stop recording & close",
            width=170,
            fg_color="#2f7d32",
            hover_color="#256528",
            command=lambda: pick("stop_and_close")
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            button_row,
            text="Keep recording",
            width=130,
            command=lambda: pick("cancel")
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            popup,
            text="Force close (video will be lost)",
            width=240,
            fg_color="#5a1f1f",
            hover_color="#4a1818",
            command=lambda: pick("force_close")
        ).pack(pady=(0, 12))

        # Treat the window X as "Keep recording" — safest default
        popup.protocol("WM_DELETE_WINDOW", lambda: pick("cancel"))

        # Block until the user picks something
        self.app.wait_window(popup)
        return choice["value"]

    def on_device_selected(self, device):
        self.selected_device = device
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
        def finish_close():
            """
            Final teardown path.
            This should only run when no recording is actively being saved.
            """
            self._stop_connection_monitor()

            if self.stream:
                try:
                    self.stream.stop()
                except Exception as e:
                    print(f"[!] Error stopping stream during close: {e}")
                self.stream = None

            if self.session:
                print(f"[+] Session ended. Evidence path: {self.session.get_evidence_path()}")

            stop_adb_server()
            self.app.destroy()

        def on_close():
            if self.recording_manager.is_stopping():
                show_toast(
                    self.app,
                    "Recording is still saving. Please wait.",
                    fg_color="#d94040",
                    duration=3000
                )
                print("[!] Close blocked: recording is still saving")
                return

            if self.recording_manager.is_recording():
                choice = self._confirm_close_while_recording()

                if choice == "cancel":
                    print("[+] Close cancelled, recording continues")
                    return

                if choice == "stop_and_close":
                    print("[+] Stopping recording before close...")

                    self.record_button.configure(state="disabled")
                    self.info_label.configure(text="Stopping recording before closing...")

                    def close_after_save(final_file_path):
                        def update_ui_and_close():
                            print(f"[+] Recording saved before close: {final_file_path}")

                            self._reset_recording_ui_after_stop()

                            if self._recording_timer_after_id is not None:
                                try:
                                    self.app.after_cancel(self._recording_timer_after_id)
                                except Exception:
                                    pass
                                self._recording_timer_after_id = None

                            finish_close()

                        self.app.after(0, update_ui_and_close)

                    def close_after_error(error):
                        def update_ui_after_error():
                            print(f"[ERROR] Failed to stop recording cleanly on close: {error}")

                            self._reset_recording_ui_after_stop()

                            show_toast(
                                self.app,
                                "Recording stop failed - check the case folder for the .mkv temp file",
                                fg_color="#d94040",
                                duration=5000
                            )

                            # Do not destroy immediately after a failed save.
                            # Safer default: keep the app open so the user can inspect the issue.
                            self.info_label.configure(
                                text="Recording stop failed - app kept open for safety"
                            )

                        self.app.after(0, update_ui_after_error)

                    self.recording_manager.stop_recording_async(
                        on_success=close_after_save,
                        on_error=close_after_error
                    )

                    return

                if choice == "force_close":
                    print("[!] Force close requested - recording may be incomplete")
                    finish_close()
                    return

            finish_close()

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
            self.update_toolbar_session_label()

            # Update window title with session info
            self.app.title(
                f"ADB Media Manager — {self.session.officer_name} — Case {self.session.case_number}"
            )

            # Optional recovery check for unfinished temp recordings
            try:
                recovered_files = self.recording_manager.recover_temp_recordings(
                    self.session.case_path
                )

                if recovered_files:
                    show_toast(
                        self.app,
                        f"Recovered {len(recovered_files)} unfinished recording(s)",
                        fg_color="#2f7d32",
                        duration=4000
                    )
                    print(f"[+] Recovered recordings: {recovered_files}")

            except Exception as e:
                print(f"[WARN] Recording recovery check failed: {e}")

            # Step 2: Device selection
            self.device_manager.show_device_selection()

        self.app.after(0, startup_flow)
        self.app.after(100, self.maximize_windowed_fullscreen)
        self.app.mainloop()

    def get_widget_relative_geometry(self, widget):
        widget.update_idletasks()
        self.app.update_idletasks()

        x = widget.winfo_rootx() - self.app.winfo_rootx()
        y = widget.winfo_rooty() - self.app.winfo_rooty()
        width = widget.winfo_width()
        height = widget.winfo_height()

        return (x, y, width, height)

    def _reset_recording_ui_after_stop(self):
        """
        Reset all recording-related UI state after the recording has stopped.
        This must run on the Tkinter main thread.
        """
        self.record_button.configure(
            text="⏺",
            fg_color="#1f6aa5",
            hover_color="#144870",
            state="normal"
        )

        self._last_sent_crop = None

        self._resize_lock_geometry = None
        self._resize_warning_active = False
        

        self.video_border_frame.configure(fg_color="black")

        if self._recording_timer_after_id is not None:
            try:
                self.app.after_cancel(self._recording_timer_after_id)
            except Exception:
                pass
            self._recording_timer_after_id = None

        self._recording_start_time = None
        self.recording_timer_label.configure(
            text="00:00:00",
            text_color="gray60"
        )

    def _on_recording_saved(self, final_file_path):
        """
        Called after async recording stop/remux succeeds.
        This method is called from the worker thread, so UI updates are forwarded
        to the Tkinter main thread using app.after().
        """
        def update_ui():
            self._reset_recording_ui_after_stop()
            self.info_label.configure(text="Recording saved")
            show_toast(
                self.app,
                "Recording saved successfully",
                fg_color="#2f7d32",
                duration=3000
            )
            print(f"[+] Recording saved: {final_file_path}")

        self.app.after(0, update_ui)
        
        
    def _on_recording_stop_failed(self, error):
        """
        Called after async recording stop/remux fails.
        This method is called from the worker thread, so UI updates are forwarded
        to the Tkinter main thread using app.after().
        """
        def update_ui():
            self._reset_recording_ui_after_stop()

            self.info_label.configure(
                text="Recording stop failed - check temp MKV file"
            )

            show_toast(
                self.app,
                "Recording stop failed - check the case folder for the .mkv temp file",
                fg_color="#d94040",
                duration=5000
            )

            print(f"[ERROR] Recording stop failed: {error}")

        self.app.after(0, update_ui)
        
        
    def toggle_recording(self):
        try:
            # Stop Recording Logic
            if self.recording_manager.is_recording():
                if self.recording_manager.is_stopping():
                    self.info_label.configure(text="Recording is already stopping...")
                    return

                self.record_button.configure(state="disabled")
                self.info_label.configure(text="Stopping recording...")

                self.recording_manager.stop_recording_async(
                    on_success=self._on_recording_saved,
                    on_error=self._on_recording_stop_failed
                )

                return

            if self.recording_manager.is_stopping():
                self.info_label.configure(text="Recording is still saving...")
                return

            if not self.session:
                self.info_label.configure(text="No active case session.")
                return

            x, y, w, h = self.get_widget_relative_geometry(self.video_canvas)
            self._last_sent_crop = (x, y, w, h)

            print(f"[DEBUG] Relative canvas geometry: x={x}, y={y}, w={w}, h={h}")
            print(f"[DEBUG] App root: x={self.app.winfo_rootx()}, y={self.app.winfo_rooty()}")
            print(f"[DEBUG] Canvas root: x={self.video_canvas.winfo_rootx()}, y={self.video_canvas.winfo_rooty()}")

            self.app.update_idletasks()

            self._resize_lock_geometry = (
                self.app.winfo_width(),
                self.app.winfo_height(),
                self.app.winfo_x(),
                self.app.winfo_y()
            )

            # Ignore internal configure events caused by UI updates during recording start.
            self._ignore_configure_until = time.time() + 0.5

            self.recording_manager.create_session(
                case_folder=self.session.case_path,
                capture_x=x,
                capture_y=y,
                capture_width=w,
                capture_height=h,
                window_title=self.app.title(),
                audio_device=None
            )

            # Start Recording Logic
            self.recording_manager.start_recording()
            
            self.app.after(500, self._check_recording_started)

            self.record_button.configure(
                text="⏹",
                fg_color="#d94040",
                hover_color="#b33030",
                state="normal"
            )

            self.info_label.configure(text="Recording started")

            # Add red border to video canvas to indicate recording
            self.video_border_frame.configure(fg_color="red")

            # Start recording timer
            self._recording_start_time = time.time()
            self.recording_timer_label.configure(text="00:00:00", text_color="red")
            self._update_recording_timer()

        except Exception as e:
            self.record_button.configure(state="normal")
            self.info_label.configure(text=f"Recording error: {str(e)}")
            print(f"[ERROR] toggle_recording: {e}")        
        
        
    def _check_recording_started(self):
        if not self.recording_manager.current_session:
            return

        if not self.recording_manager.is_recording():
            self.info_label.configure(text="Recording failed to start")
            self.record_button.configure(
                text="⏺",
                fg_color="#1f6aa5",
                hover_color="#144870",
                state="normal"
            )
            self.video_border_frame.configure(fg_color="black")
            
            return

        print("[+] Recording confirmed running after startup check")
   
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
        
    def _on_window_configure(self, event):
        """
        Soft-lock window resizing while recording.

        Instead of using app.resizable(False, False), which can cause a full white
        redraw/flicker on Windows, we keep the window technically resizable but
        restore it back to the locked size if the user changes it.
        """
        if event.widget != self.app:
            return

        if not hasattr(self, "recording_manager"):
            return

        if not self.recording_manager.is_recording():
            return

        if not self._resize_lock_geometry:
            return

        # Ignore configure events triggered internally during recording start.
        if time.time() < self._ignore_configure_until:
            return

        # Avoid reacting to our own geometry restore.
        if self._is_restoring_locked_geometry:
            return

        locked_width, locked_height, locked_x, locked_y = self._resize_lock_geometry

        current_width = self.app.winfo_width()
        current_height = self.app.winfo_height()
        current_x = self.app.winfo_x()
        current_y = self.app.winfo_y()

        size_changed = (
            current_width != locked_width
            or current_height != locked_height
        )

        position_changed = (
            current_x != locked_x
            or current_y != locked_y
        )

        # Only block actual resize, not normal internal layout/configure events.
        if not size_changed:
            return

        if self._resize_restore_after_id is not None:
            return

        def restore_locked_size():
            self._resize_restore_after_id = None

            if not self.recording_manager.is_recording():
                return

            if not self._resize_lock_geometry:
                return

            self._is_restoring_locked_geometry = True

            try:
                geometry = f"{locked_width}x{locked_height}+{locked_x}+{locked_y}"
                self.app.geometry(geometry)
            finally:
                self.app.after(100, lambda: setattr(self, "_is_restoring_locked_geometry", False))

            if not self._resize_warning_active:
                self._resize_warning_active = True

                show_toast(
                    self.app,
                    "Window resizing is disabled while recording",
                    fg_color="#d94040",
                    duration=3000
                )

                self.app.after(
                    3200,
                    lambda: setattr(self, "_resize_warning_active", False)
                )

            print("[!] Resize blocked: recording is active and dynamic crop update is disabled")

        self._resize_restore_after_id = self.app.after_idle(restore_locked_size)


if __name__ == "__main__":
    app = MediaDisplayApp()
    app.run()
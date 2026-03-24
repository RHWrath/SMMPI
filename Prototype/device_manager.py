import customtkinter as ctk
from ppadb.client import Client as AdbClient

class DeviceManager:
    def __init__(self, app, on_device_selected):
        self.app = app
        self.on_device_selected = on_device_selected
        self.device_window = None
        self.device_listbox = None
        self.status_label = None
        self.available_devices = []
        self.selected_device_index = None
        self.selected_device = None

    def show_device_selection(self):
        try:
            self.app.deiconify()
            self.app.update()
            self.app.attributes("-alpha", 0.0)
        except Exception:
            pass

        device_window = ctk.CTkToplevel(self.app)
        device_window.title("Select Android Device")
        device_window.geometry("500x400")
        device_window.transient(self.app)
        device_window.grab_set()

        device_window.geometry("+{}+{}".format(
            int(self.app.winfo_screenwidth() / 2 - 250),
            int(self.app.winfo_screenheight() / 2 - 200)
        ))

        title_label = ctk.CTkLabel(
            device_window,
            text="Connect Android Device",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=20)

        instructions = ctk.CTkLabel(
            device_window,
            text="Make sure USB debugging is enabled on your device\nand it's connected via USB.",
            font=("Arial", 12)
        )
        instructions.pack(pady=10)

        refresh_button = ctk.CTkButton(
            device_window,
            text="Refresh Devices",
            command=lambda: self.refresh_device_list()
        )
        refresh_button.pack(pady=10)

        device_listbox = ctk.CTkScrollableFrame(device_window, height=150)
        device_listbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.device_listbox = device_listbox

        status_label = ctk.CTkLabel(device_window, text="Click 'Refresh Devices' to scan for devices")
        status_label.pack(pady=5)
        self.status_label = status_label

        button_frame = ctk.CTkFrame(device_window, fg_color="transparent")
        button_frame.pack(pady=10)

        connect_button = ctk.CTkButton(
            button_frame,
            text="Connect",
            command=lambda: self.connect_device()
        )
        connect_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=lambda: self.cancel_device_selection()
        )
        cancel_button.pack(side="left", padx=10)

        self.device_window = device_window
        self.refresh_device_list()
        device_window.wait_window()

        try:
            self.app.attributes("-alpha", 1.0)
            self.app.deiconify()
            self.app.update()
            self.app.lift()
            self.app.focus_force()
        except Exception as e:
            print(f"Error showing main window after device selection: {e}")

        if self.selected_device_index is None or not self.available_devices:
            self.app.quit()

    def refresh_device_list(self):
        try:
            client = AdbClient(host="127.0.0.1", port=5037)
            devices = client.devices()

            for widget in self.device_listbox.winfo_children():
                widget.destroy()

            self.available_devices = []

            if not devices:
                self.status_label.configure(text="No devices found. Check USB debugging and connection.")
                return

            self.status_label.configure(text=f"Found {len(devices)} device(s). Select one to continue.")

            for i, device in enumerate(devices):
                try:
                    model = device.shell("getprop ro.product.model").strip()
                    manufacturer = device.shell("getprop ro.product.manufacturer").strip()
                except Exception:
                    model = "Unknown"
                    manufacturer = "Unknown"

                self.available_devices.append(device)

                device_text = f"{manufacturer} {model}\nSerial: {device.serial}"

                def make_select_command(index):
                    return lambda: self.select_device_by_index(index)

                device_button = ctk.CTkButton(
                    self.device_listbox,
                    text=device_text,
                    height=60,
                    command=make_select_command(i),
                    fg_color=("gray90", "gray20"),
                    hover_color=("gray70", "gray40")
                )
                device_button.pack(fill="x", pady=5)

        except Exception as e:
            self.status_label.configure(text=f"Error scanning devices: {str(e)}")

    def select_device_by_index(self, index):
        self.selected_device_index = index
        if index < len(self.available_devices):
            self.selected_device = self.available_devices[index]
            try:
                model = self.selected_device.shell("getprop ro.product.model").strip()
                manufacturer = self.selected_device.shell("getprop ro.product.manufacturer").strip()
                device_name = f"{manufacturer} {model}"
            except Exception:
                device_name = self.selected_device.serial

            self.status_label.configure(
                text=f"✓ Selected: {device_name}.",
                text_color="green"
            )

            self.connect_device()

    def connect_device(self):
        if self.selected_device_index is not None and self.available_devices:
            self.selected_device = self.available_devices[self.selected_device_index]
            try:
                self.on_device_selected(self.selected_device)

                self.device_window.destroy()

                self.app.deiconify()
                self.app.update()
                self.app.lift()
                self.app.focus_force()
            except Exception as e:
                print(f"connect_device: Error restoring main window - {e}")
        else:
            self.status_label.configure(text="Please select a device first")

    def cancel_device_selection(self):
        self.selected_device = None
        self.device_window.destroy()

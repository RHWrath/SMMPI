import customtkinter as ctk
from tkinter import Canvas


def show_toast(parent, message, duration=2500, fg_color="#2fa572", text_color="white"):
    """
    Show a toast-style notification that auto-dismisses.
    Floats at the top-center of the parent window.
    """
    toast = ctk.CTkFrame(
        parent,
        fg_color=fg_color,
        corner_radius=16,
    )

    label = ctk.CTkLabel(
        toast,
        text=message,
        font=("Arial", 14, "bold"),
        text_color=text_color,
    )
    label.pack(padx=20, pady=10)

    # Place it top-center of the window
    toast.place(relx=0.5, rely=0.04, anchor="n")

    # Lift above all other widgets
    toast.lift()

    # Auto-dismiss after duration
    parent.after(duration, lambda: toast.destroy())


class UISetup:
    @staticmethod
    def create_main_frame(parent):
        main_frame = ctk.CTkFrame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=2)
        main_frame.grid_rowconfigure(0, weight=1)

        return main_frame

    @staticmethod
    def setup_left_panel(parent, on_folder_select_callback):
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        control_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        control_frame.pack(fill="x", padx=5, pady=5)

        select_button = ctk.CTkButton(
            control_frame,
            text="Select Folder",
            corner_radius=32,
            command=on_folder_select_callback,
            font=("Arial", 14)
        )
        select_button.pack(pady=(0, 10))

        folder_path_label = ctk.CTkLabel(
            control_frame,
            text="No folder selected",
            font=("Arial", 10),
            wraplength=300
        )
        folder_path_label.pack()

        media_scroll_frame = ctk.CTkScrollableFrame(left_panel)
        media_scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        return left_panel, select_button, folder_path_label, media_scroll_frame

    @staticmethod
    def setup_middle_panel(parent, on_image_confirm_callback=None):
        middle_panel = ctk.CTkFrame(parent)
        middle_panel.grid(row=0, column=1, sticky="nsew", padx=5)

        info_label = ctk.CTkLabel(
            middle_panel,
            text="Select a folder to display images and videos",
            font=("Arial", 10)
        )
        info_label.pack(pady=(10, 0))

        confirm_button = ctk.CTkButton(
            middle_panel,
            text="Confirm Selection",
            corner_radius=32,
            command=on_image_confirm_callback,
            font=("Arial", 14)
        )
        confirm_button.pack(pady=(0, 10))

        return middle_panel, info_label

    @staticmethod
    def setup_right_panel(parent):
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

        title_label = ctk.CTkLabel(
            right_panel,
            text="Device Screen",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(10, 5))

        video_canvas = Canvas(
            right_panel,
            bg="black",
            highlightthickness=0
        )
        video_canvas.pack(pady=5, fill="both", expand=True)

        status_label = ctk.CTkLabel(
            right_panel,
            text="Stream will display here - click to interact",
            font=("Arial", 10)
        )
        status_label.pack(pady=10)

        return right_panel, video_canvas, status_label
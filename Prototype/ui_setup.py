import customtkinter as ctk
from tkinter import Canvas
from about_software_manager import AboutSoftwareManager
from lang import t


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
        main_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=4)
        main_frame.grid_rowconfigure(0, weight=4)
        main_frame.grid_rowconfigure(1, weight=1)

        return main_frame

    @staticmethod
    def setup_left_panel(parent, on_folder_select_callback):
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        control_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        control_frame.pack(fill="x", padx=5, pady=5)

        select_button = ctk.CTkButton(
            control_frame,
            text=t("btn_select_folder"),
            corner_radius=32,
            command=on_folder_select_callback,
            font=("Arial", 14)
        )
        select_button.pack(pady=(0, 10))

        folder_path_label = ctk.CTkLabel(
            control_frame,
            text=t("no_folder_selected"),
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
        middle_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 5))

        info_label = ctk.CTkLabel(
            middle_panel,
            text=t("select_folder_prompt"),
            font=("Arial", 10)
        )
        info_label.pack(pady=(10, 0))

        confirm_button = ctk.CTkButton(
            middle_panel,
            text=t("btn_confirm_selection"),
            corner_radius=32,
            command=on_image_confirm_callback,
            font=("Arial", 14)
        )
        confirm_button.pack(pady=(0, 10))

        return middle_panel, info_label

    @staticmethod
    def _attach_tooltip(widget, text):
        """
        Show a small label tooltip on hover.

        `text` may be a plain string or a zero-arg callable returning a string.
        Using a callable lets the tooltip reflect the active language even if
        it changed after the widget was created.
        """
        tip = None

        def resolve_text():
            return text() if callable(text) else text

        def on_enter(e):
            nonlocal tip
            x = widget.winfo_rootx() + widget.winfo_width() // 2
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tip = ctk.CTkToplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            ctk.CTkLabel(tip, text=resolve_text(), font=("Arial", 11),
                         fg_color="#2b2b2b", corner_radius=6).pack(padx=8, pady=4)

        def on_leave(e):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    @staticmethod
    def setup_right_panel(parent):
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))

        header_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        title_label = ctk.CTkLabel(
            header_frame,
            text=t("device_screen"),
            font=("Arial", 14, "bold")
        )
        title_label.pack(side="left", pady=(10, 5))
        # Exposed so the language re-apply can re-translate it after the picker.
        right_panel.device_screen_title = title_label

        recording_timer_label = ctk.CTkLabel(
            header_frame,
            text="00:00:00",
            font=("Arial", 13, "bold"),
            text_color="gray60"
        )
        recording_timer_label.pack(side="right", pady=(10, 5))

        record_button = ctk.CTkButton(
            header_frame,
            text="⏺",
            width=36,
            height=36,
            corner_radius=18,
            font=("Arial", 16),
            fg_color="#2fa572",
            hover_color="#268a5f",
        )
        record_button.pack(side="right", padx=(0, 8), pady=(10, 5))
        UISetup._attach_tooltip(record_button, lambda: t("tooltip_start_recording"))

        close_app_button = ctk.CTkButton(
            header_frame,
            text="⌂",
            width=36,
            height=36,
            corner_radius=18,
            font=("Arial", 16),
            fg_color="#1f6aa5",
            hover_color="#144870",
            state="disabled",
        )
        close_app_button.pack(side="right", padx=(0, 4), pady=(10, 5))
        UISetup._attach_tooltip(close_app_button, lambda: t("tooltip_close_app"))

        video_container = ctk.CTkFrame(
            right_panel,
            fg_color="transparent",
            corner_radius=0
        )
        video_container.pack(pady=5, fill="both", expand=True)

        video_border_frame = ctk.CTkFrame(
            video_container,
            fg_color="black",
            corner_radius=0
        )
        video_border_frame.pack(fill="both", expand=True)

        video_canvas = Canvas(
            video_border_frame,
            bg="black",
            highlightthickness=0,
            bd=0
        )
        video_canvas.pack(padx=2, pady=2, fill="both", expand=True)

        status_label = ctk.CTkLabel(
            right_panel,
            text="",
            font=("Arial", 10)
        )
        # Not packed — kept as attribute only

        return right_panel, video_border_frame, video_canvas, status_label, close_app_button, record_button, recording_timer_label

    @staticmethod
    def setup_topbar(parent, on_menu_click):
        topbar = ctk.CTkFrame(
            parent,
            height=56,
            fg_color="#1f1f1f",
            corner_radius=0
        )
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        menu_button = ctk.CTkButton(
            topbar,
            text="☰",
            width=40,
            height=32,
            font=("Arial", 18, "bold"),
            fg_color="transparent",
            hover_color="#333333",
            command=on_menu_click
        )
        menu_button.pack(side="left", padx=(12, 8), pady=0)

        session_label = ctk.CTkLabel(
            topbar,
            text=t("no_active_session"),
            font=("Arial", 11),
            text_color="#4A9EFF"
        )
        session_label.pack(side="left", padx=(8, 0), pady=0)

        return topbar, menu_button, session_label

    @staticmethod
    def setup_sidebar(parent, on_new_case, on_open_case, on_add_platform=None, on_manage_platforms=None):
        sidebar = ctk.CTkFrame(
            parent,
            width=220,
            fg_color="#181818",
            corner_radius=0
        )

        new_case_btn = ctk.CTkButton(
            sidebar,
            text=t("sidebar_new_case"),
            command=on_new_case
        )
        new_case_btn.pack(fill="x", padx=10, pady=(15, 5))

        open_case_btn = ctk.CTkButton(
            sidebar,
            text=t("sidebar_switch_case"),
            command=on_open_case
        )
        open_case_btn.pack(fill="x", padx=10, pady=5)

        # Divider label for platform section
        platform_section_label = ctk.CTkLabel(
            sidebar,
            text=t("sidebar_platforms"),
            font=("Arial", 10),
            text_color="gray50"
        )
        # Hidden until login — revealed by main.py after session starts
        # platform_section_label.pack(...)

        add_platform_btn = ctk.CTkButton(
            sidebar,
            text=t("sidebar_add_platform"),
            command=on_add_platform
        )
        add_platform_btn.pack(fill="x", padx=10, pady=(25, 5))
        # Hidden until login

        manage_platforms_btn = ctk.CTkButton(
            sidebar,
            text=t("sidebar_manage_platforms"),
            command=on_manage_platforms
        )
        manage_platforms_btn.pack(fill="x", padx=10, pady=5)
        # Hidden until login

        # settings_btn = ctk.CTkButton(
        #    sidebar,
        #    text="Settings"
        # )
        # settings_btn.pack(fill="x", padx=10, pady=(25, 5))

        return sidebar, new_case_btn, open_case_btn, platform_section_label, add_platform_btn, manage_platforms_btn

    @staticmethod
    def show_about_popup(parent):
        """
        Shows application version information and release notes.
        This belongs to UISetup because it only builds the popup UI.
        The version/release data is loaded by AboutSoftwareManager.
        """
        version_info = AboutSoftwareManager.load_version_info()
        release_notes = AboutSoftwareManager.load_release_notes()

        popup = ctk.CTkToplevel(parent)
        popup.title(t("about_window_title"))
        popup.geometry("620x520")
        popup.minsize(520, 420)
        popup.transient(parent)
        popup.grab_set()

        popup.geometry("+{}+{}".format(
            int(parent.winfo_screenwidth() / 2 - 310),
            int(parent.winfo_screenheight() / 2 - 260)
        ))

        container = ctk.CTkFrame(popup)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        title_label = ctk.CTkLabel(
            container,
            text=version_info["app_name"],
            font=("Arial", 20, "bold"),
            text_color="#4A9EFF"
        )
        title_label.pack(anchor="w", pady=(0, 6))

        version_label = ctk.CTkLabel(
            container,
            text=t("about_version", version=version_info["version"]),
            font=("Arial", 13),
            text_color="gray90"
        )
        version_label.pack(anchor="w")

        build_label = ctk.CTkLabel(
            container,
            text=t("about_build", build=version_info["build"]),
            font=("Arial", 12),
            text_color="gray65"
        )
        build_label.pack(anchor="w", pady=(0, 6))

        description_label = ctk.CTkLabel(
            container,
            text=version_info["description"],
            font=("Arial", 12),
            text_color="gray65",
            wraplength=560,
            justify="left"
        )
        description_label.pack(anchor="w", pady=(0, 14))

        release_title = ctk.CTkLabel(
            container,
            text=t("about_release_notes"),
            font=("Arial", 15, "bold")
        )
        release_title.pack(anchor="w", pady=(4, 6))

        release_textbox = ctk.CTkTextbox(
            container,
            wrap="word",
            font=("Consolas", 11)
        )
        release_textbox.pack(fill="both", expand=True)

        release_textbox.insert("1.0", release_notes)
        release_textbox.configure(state="disabled")

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(fill="x", pady=(14, 0))

        close_button = ctk.CTkButton(
            button_row,
            text=t("btn_close"),
            width=120,
            command=popup.destroy
        )
        close_button.pack(side="right")

        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
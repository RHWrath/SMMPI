import customtkinter as ctk
import os

from config_manager import load_config, save_config
from session import Session


class CaseManager:
    """Handles the login and case selection flow before the main app starts."""

    def __init__(self, app):
        self.app = app
        self.config = load_config()
        self.session = None

        self._officer_name = None
        self._case_number = None

    def run_login_flow(self):
        """
        Show login screen, then case selection screen.
        Returns a Session object or None if cancelled.
        """
        self._show_login_screen()

        if not self._officer_name:
            return None

        self._show_case_selection_screen()

        if not self._case_number:
            return None

        # Build session and ensure the case folder exists
        self.session = Session(
            officer_name=self._officer_name,
            case_number=self._case_number,
            case_root=self.config["case_root"]
        )
        self.session.ensure_case_folder()

        print(f"[+] Session started: officer='{self.session.officer_name}', "
              f"case='{self.session.case_number}', path='{self.session.case_path}'")
        print(f"[+] Evidence will save as: {self.session.get_evidence_filename()}")

        return self.session

    # ── Login Screen ──────────────────────────────────────────────────

    def _show_login_screen(self):
        login_window = ctk.CTkToplevel(self.app)
        login_window.title("Officer Login")
        login_window.geometry("400x250")
        login_window.resizable(False, False)
        login_window.transient(self.app)
        login_window.grab_set()

        login_window.geometry("+{}+{}".format(
            int(self.app.winfo_screenwidth() / 2 - 200),
            int(self.app.winfo_screenheight() / 2 - 125)
        ))

        title_label = ctk.CTkLabel(
            login_window,
            text="SMMPI - Officer Login",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=(30, 20))

        name_frame = ctk.CTkFrame(login_window, fg_color="transparent")
        name_frame.pack(pady=10, padx=40, fill="x")

        name_label = ctk.CTkLabel(
            name_frame,
            text="Name:",
            font=("Arial", 14)
        )
        name_label.pack(anchor="w")

        name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="Enter your name",
            font=("Arial", 14),
            height=36
        )
        name_entry.pack(fill="x", pady=(5, 0))
        name_entry.focus_set()

        error_label = ctk.CTkLabel(
            login_window,
            text="",
            font=("Arial", 11),
            text_color="red"
        )
        error_label.pack(pady=(5, 0))

        def on_continue():
            name = name_entry.get().strip()
            if not name:
                error_label.configure(text="Please enter your name")
                return
            self._officer_name = name
            login_window.destroy()

        def on_cancel():
            self._officer_name = None
            login_window.destroy()

        # Bind Enter key
        name_entry.bind("<Return>", lambda e: on_continue())

        button_frame = ctk.CTkFrame(login_window, fg_color="transparent")
        button_frame.pack(pady=15)

        continue_button = ctk.CTkButton(
            button_frame,
            text="Continue",
            command=on_continue,
            font=("Arial", 14),
            width=120
        )
        continue_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=on_cancel,
            font=("Arial", 14),
            width=120,
            fg_color="gray40",
            hover_color="gray30"
        )
        cancel_button.pack(side="left", padx=10)

        login_window.protocol("WM_DELETE_WINDOW", on_cancel)
        login_window.wait_window()

    # ── Case Selection Screen ─────────────────────────────────────────

    def _show_case_selection_screen(self):
        case_window = ctk.CTkToplevel(self.app)
        case_window.title("Select Case")
        case_window.geometry("550x500")
        case_window.resizable(False, False)
        case_window.transient(self.app)
        case_window.grab_set()

        case_window.geometry("+{}+{}".format(
            int(self.app.winfo_screenwidth() / 2 - 275),
            int(self.app.winfo_screenheight() / 2 - 250)
        ))

        # ── Header ──
        header_frame = ctk.CTkFrame(case_window, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))

        title_label = ctk.CTkLabel(
            header_frame,
            text=f"Welcome, {self._officer_name}",
            font=("Arial", 18, "bold")
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Select an existing case or create a new one",
            font=("Arial", 12),
            text_color="gray60"
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # ── Case root display + change button ──
        root_frame = ctk.CTkFrame(case_window, fg_color="transparent")
        root_frame.pack(fill="x", padx=20, pady=(5, 10))

        root_path_label = ctk.CTkLabel(
            root_frame,
            text=f"Case folder: {self.config['case_root']}",
            font=("Arial", 10),
            text_color="gray50"
        )
        root_path_label.pack(side="left", fill="x", expand=True, anchor="w")

        def change_root():
            from customtkinter import filedialog
            new_root = filedialog.askdirectory(
                title="Select Case Root Folder",
                initialdir=self.config["case_root"]
            )
            if new_root:
                self.config["case_root"] = new_root
                save_config(self.config)
                root_path_label.configure(text=f"Case folder: {new_root}")
                refresh_case_list()

        change_root_button = ctk.CTkButton(
            root_frame,
            text="Change",
            command=change_root,
            font=("Arial", 11),
            width=70,
            height=26,
            fg_color="gray40",
            hover_color="gray30"
        )
        change_root_button.pack(side="right")

        # ── New case entry ──
        new_case_frame = ctk.CTkFrame(case_window, fg_color="transparent")
        new_case_frame.pack(fill="x", padx=20, pady=(0, 10))

        new_case_entry = ctk.CTkEntry(
            new_case_frame,
            placeholder_text="Enter new case number",
            font=("Arial", 13),
            height=34
        )
        new_case_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def on_new_case():
            case_num = new_case_entry.get().strip()
            if not case_num:
                error_label.configure(text="Please enter a case number")
                return
            # Basic filename safety check
            if any(c in case_num for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                error_label.configure(text="Case number contains invalid characters")
                return
            self._case_number = case_num
            case_window.destroy()

        new_case_button = ctk.CTkButton(
            new_case_frame,
            text="New Case",
            command=on_new_case,
            font=("Arial", 13),
            width=100,
            height=34
        )
        new_case_button.pack(side="right")

        new_case_entry.bind("<Return>", lambda e: on_new_case())

        # ── Existing cases list ──
        list_label = ctk.CTkLabel(
            case_window,
            text="Existing Cases",
            font=("Arial", 13, "bold")
        )
        list_label.pack(anchor="w", padx=20, pady=(0, 5))

        case_list_frame = ctk.CTkScrollableFrame(
            case_window,
            height=220
        )
        case_list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        error_label = ctk.CTkLabel(
            case_window,
            text="",
            font=("Arial", 11),
            text_color="red"
        )
        error_label.pack(pady=(0, 5))

        def refresh_case_list():
            for widget in case_list_frame.winfo_children():
                widget.destroy()

            case_root = self.config["case_root"]

            if not os.path.exists(case_root):
                no_cases_label = ctk.CTkLabel(
                    case_list_frame,
                    text="No cases found. Create a new case to get started.",
                    font=("Arial", 12),
                    text_color="gray50"
                )
                no_cases_label.pack(pady=20)
                return

            # List directories in case root
            try:
                entries = sorted([
                    d for d in os.listdir(case_root)
                    if os.path.isdir(os.path.join(case_root, d))
                ])
            except OSError as e:
                print(f"[!] Error listing case root: {e}")
                entries = []

            if not entries:
                no_cases_label = ctk.CTkLabel(
                    case_list_frame,
                    text="No cases found. Create a new case to get started.",
                    font=("Arial", 12),
                    text_color="gray50"
                )
                no_cases_label.pack(pady=20)
                return

            for case_name in entries:
                case_path = os.path.join(case_root, case_name)

                # Count existing evidence files
                try:
                    file_count = len([
                        f for f in os.listdir(case_path)
                        if os.path.isfile(os.path.join(case_path, f))
                    ])
                except OSError:
                    file_count = 0

                def make_select(cn):
                    return lambda: select_case(cn)

                case_button = ctk.CTkButton(
                    case_list_frame,
                    text=f"  {case_name}\n  {file_count} file(s)",
                    font=("Arial", 13),
                    anchor="w",
                    height=50,
                    command=make_select(case_name),
                    fg_color=("gray85", "gray20"),
                    hover_color=("gray70", "gray35"),
                    text_color=("gray10", "gray90")
                )
                case_button.pack(fill="x", pady=3)

        def select_case(case_name):
            self._case_number = case_name
            case_window.destroy()

        def on_cancel():
            self._case_number = None
            case_window.destroy()

        # ── Bottom buttons ──
        bottom_frame = ctk.CTkFrame(case_window, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(0, 15))

        cancel_button = ctk.CTkButton(
            bottom_frame,
            text="Cancel",
            command=on_cancel,
            font=("Arial", 13),
            width=100,
            fg_color="gray40",
            hover_color="gray30"
        )
        cancel_button.pack(side="right")

        case_window.protocol("WM_DELETE_WINDOW", on_cancel)

        refresh_case_list()
        case_window.wait_window()
        
    def select_case_for_current_officer(self, officer_name: str):
        """
        Re-open only the case selection screen for an already known officer.
        Returns a Session or None if cancelled.
        """
        self._officer_name = officer_name
        self._case_number = None
        
        if not self._case_number:
            return None
        
        self.session = Session(
            officer_name=self._officer_name,
            case_number=self._case_number,
            case_root=self.config["case_root"]
        )
        self.session.ensure_case_folder()
        
        print(f"[+] Session changed: officer='{self.session.officer_name}', "f"case='{self.session.case_number}', path='{self.session.case_path}'")
        print(f"[+] Evidence will save as: {self.session.get_evidence_filename()}")            
        return self.session
        

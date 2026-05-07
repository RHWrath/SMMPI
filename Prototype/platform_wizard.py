# stdlib
import json
import os
import re
import shutil

# third-party
import customtkinter as ctk

# internal
from utils import get_platforms_file
from platform_management import get_foreground_package, load_platforms
from ui_setup import show_toast


# ---- Defaults & constants -------------------------------------------------
# Defaults match the gallery-push platforms (WhatsApp/Discord) since that's
# the most common path for newly added platforms.
DEFAULT_GALLERY_PATH = "/storage/emulated/0/DCIM/Camera/"


DEFAULT_PHOTO_SPECS = {
    "width": "4032",
    "height": "3024",
    "rotate": "",          # blank = null in JSON
    "mirror": "false",
    "resize_mode": "contain",
    "filename": "virtual_photo.jpg",
}

DEFAULT_VIDEO_SPECS = {
    "width": "1920",
    "height": "1080",
    "rotate": "",
    "mirror": "false",
    "resize_mode": "contain",
    "max_duration": "60",
    "filename": "virtual.mp4",
}

# com.example.app — at least two segments, lowercase letters/digits/underscores
PACKAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
RESIZE_MODES = ["contain", "fill", "cover", "stretch"]
PHOTO_MODES = ["gallery", "vcam"]
package = ""


# ============================================================================
# Base — owns the shared form, validation, and save logic
# ============================================================================

class _PlatformFormBase:
    """
    Base class owning the shared form (identity, photo mode, photo + video
    specs), validation, and the save-to-disk logic. Subclasses provide the
    window title, button label, header section, and how to apply the saved
    config to platforms.json.
    """

    # Subclasses override
    WINDOW_TITLE = "Platform"
    SAVE_BUTTON_LABEL = "Save"
    HEADER_TITLE = "Platform"
    HEADER_SUBTITLE = ""

    def __init__(self, parent, on_saved=None):
        self.parent = parent
        self.on_saved = on_saved
        self.result_saved = False

        # Index of the platform being edited (None = add mode).
        # Add subclass leaves this None; edit subclass sets it.
        self._edit_index = None

        self.win = ctk.CTkToplevel(parent)
        self.win.title(self.WINDOW_TITLE)
        self.win.geometry("640x820")
        self.win.transient(parent)
        self.win.grab_set()

        try:
            self.existing_platforms = load_platforms()
        except Exception as e:
            print(f"[ERROR] Could not load existing platforms: {e}")
            self.existing_platforms = []

        self._build_ui()
        self._on_photo_mode_change()  # apply initial visibility

    # ---- UI construction -------------------------------------------------

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self.win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self._scroll = scroll

        ctk.CTkLabel(
            scroll,
            text=self.HEADER_TITLE,
            font=("Arial", 18, "bold"),
        ).pack(pady=(5, 2))

        if self.HEADER_SUBTITLE:
            ctk.CTkLabel(
                scroll,
                text=self.HEADER_SUBTITLE,
                font=("Arial", 11),
                text_color="gray",
            ).pack(pady=(0, 12))

        # Hook for subclasses to inject content above the identity section
        self._build_pre_form(scroll)

        # Platform identity ------------------------------------------------
        self._section_label(scroll, "Platform identity")

        self.name_entry = self._labeled_entry(
            scroll, "Platform name (e.g. Instagram)"
        )

        # Package row with Detect button
        package_block = ctk.CTkFrame(scroll, fg_color="transparent")
        package_block.pack(fill="x", padx=4, pady=(0, 6))
        ctk.CTkLabel(
            package_block,
            text="Package name (e.g. com.instagram.android)",
            font=("Arial", 11),
        ).pack(anchor="w")

        entry_row = ctk.CTkFrame(package_block, fg_color="transparent")
        entry_row.pack(fill="x")
        self.package_entry = ctk.CTkEntry(entry_row)
        self.package_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            entry_row,
            text="Detect from phone",
            width=140,
            command=self._detect_package,
        ).pack(side="right")

        ctk.CTkLabel(
            package_block,
            text="Open the target app on the phone and bring it to the foreground, then click Detect.",
            font=("Arial", 9),
            text_color="gray",
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        # Photo mode -------------------------------------------------------
        self._section_label(scroll, "Photo delivery method")

        ctk.CTkLabel(
            scroll,
            text=(
                "gallery — push photo to phone gallery (works for apps with "
                "hardened cameras like WhatsApp/Discord)\n"
                "vcam — feed photo through the virtual camera (Snapchat-style)"
            ),
            font=("Arial", 10),
            text_color="gray",
            justify="left",
            wraplength=600,
        ).pack(anchor="w", padx=4, pady=(0, 6))

        self.photo_mode_var = ctk.StringVar(value="gallery")
        mode_row = ctk.CTkFrame(scroll, fg_color="transparent")
        mode_row.pack(fill="x", padx=4, pady=(0, 6))
        for mode in PHOTO_MODES:
            ctk.CTkRadioButton(
                mode_row,
                text=mode,
                variable=self.photo_mode_var,
                value=mode,
                command=self._on_photo_mode_change,
            ).pack(side="left", padx=(0, 16))

        # Path fields (one is shown depending on photo_mode)
        self.gallery_path_entry = self._labeled_entry(
            scroll,
            "Gallery path on phone",
            default=DEFAULT_GALLERY_PATH,
        )
        self.remote_folder_entry = self._labeled_entry(
            scroll,
            "Remote folder (the folder VCAM watches on the phone)",
            default= ""
        )

        # Photo specs ------------------------------------------------------
        self._section_label(scroll, "Photo specs")
        self.photo_widgets = self._spec_block(scroll, DEFAULT_PHOTO_SPECS, include_max_duration=False)

        # Video specs ------------------------------------------------------
        self._section_label(scroll, "Video specs")
        self.video_widgets = self._spec_block(scroll, DEFAULT_VIDEO_SPECS, include_max_duration=True)

        # Buttons ----------------------------------------------------------
        btn_row = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color="#555555",
            hover_color="#3d3d3d",
            command=self._cancel,
        ).pack(side="right", padx=(6, 0))

        self.save_button = ctk.CTkButton(
            btn_row,
            text=self.SAVE_BUTTON_LABEL,
            command=self._save,
        )
        self.save_button.pack(side="right")

    def _build_pre_form(self, scroll):
        """Hook for subclasses (e.g. the editor adds a platform picker here)."""
        pass

    # ---- UI helpers ------------------------------------------------------

    def _section_label(self, parent, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=4, pady=(10, 4))

    def _labeled_entry(self, parent, label_text, default=""):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill="x", padx=4, pady=(0, 6))
        ctk.CTkLabel(block, text=label_text, font=("Arial", 11)).pack(anchor="w")
        entry = ctk.CTkEntry(block)
        if default:
            entry.insert(0, default)
        entry.pack(fill="x")
        return entry

    def _spec_block(self, parent, defaults, include_max_duration):
        """Build a grid of spec entries. Returns a dict of name -> widget."""
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill="x", padx=4, pady=(0, 4))

        widgets = {}

        def add_entry(row, col, label, key):
            cell = ctk.CTkFrame(block, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="ew", padx=(0, 6), pady=2)
            ctk.CTkLabel(cell, text=label, font=("Arial", 10)).pack(anchor="w")
            entry = ctk.CTkEntry(cell)
            entry.insert(0, defaults.get(key, ""))
            entry.pack(fill="x")
            widgets[key] = entry

        def add_combo(row, col, label, key, values):
            cell = ctk.CTkFrame(block, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="ew", padx=(0, 6), pady=2)
            ctk.CTkLabel(cell, text=label, font=("Arial", 10)).pack(anchor="w")
            combo = ctk.CTkComboBox(cell, values=values)
            combo.set(defaults.get(key, values[0]))
            combo.pack(fill="x")
            widgets[key] = combo

        add_entry(0, 0, "Width", "width")
        add_entry(0, 1, "Height", "height")
        add_entry(1, 0, "Rotate (0/90/180/270, blank = none)", "rotate")
        add_combo(1, 1, "Mirror", "mirror", ["false", "true"])
        add_combo(2, 0, "Resize mode", "resize_mode", RESIZE_MODES)
        add_entry(2, 1, "Filename", "filename")
        if include_max_duration:
            add_entry(3, 0, "Max duration (seconds)", "max_duration")

        block.grid_columnconfigure(0, weight=1)
        block.grid_columnconfigure(1, weight=1)
        return widgets

    def _on_photo_mode_change(self):
        mode = self.photo_mode_var.get()
        if mode == "gallery":
            self.gallery_path_entry.master.pack(fill="x", padx=4, pady=(0, 6))
            self.remote_folder_entry.master.pack_forget()
        else:  # vcam
            self.gallery_path_entry.master.pack_forget()
            self.remote_folder_entry.master.pack(fill="x", padx=4, pady=(0, 6))

    # ---- Form helpers (used by edit subclass for pre-filling) -----------

    def _set_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def _set_entry_or_combo(self, widget, value):
        if hasattr(widget, "set") and not hasattr(widget, "delete"):
            widget.set(value)
        else:
            try:
                widget.delete(0, "end")
                widget.insert(0, value)
            except Exception:
                if hasattr(widget, "set"):
                    widget.set(value)

    def _populate_form_from_platform(self, p):
        """Pre-fill every form field from an existing platform dict."""
        self._set_entry(self.name_entry, p.get("name", ""))
        self._set_entry(self.package_entry, p.get("package_name", ""))

        self.photo_mode_var.set(p.get("photo_mode", "gallery"))
        self._on_photo_mode_change()

        self._set_entry(self.gallery_path_entry, p.get("gallery_path") or "")
        self._set_entry(self.remote_folder_entry, p.get("remote_folder") or "")

        self._fill_spec_widgets(self.photo_widgets, p.get("photo", {}) or {}, include_max_duration=False)
        self._fill_spec_widgets(self.video_widgets, p.get("video", {}) or {}, include_max_duration=True)

    def _fill_spec_widgets(self, widgets, spec, include_max_duration):
        for key in ("width", "height", "filename", "resize_mode"):
            if key in widgets:
                self._set_entry_or_combo(widgets[key], str(spec.get(key, "")))

        rotate = spec.get("rotate")
        self._set_entry_or_combo(widgets["rotate"], "" if rotate is None else str(rotate))

        mirror = spec.get("mirror")
        if mirror is True:
            mirror_str = "true"
        elif mirror is False:
            mirror_str = "false"
        else:
            mirror_str = "false"
        self._set_entry_or_combo(widgets["mirror"], mirror_str)

        if include_max_duration and "max_duration" in widgets:
            self._set_entry_or_combo(widgets["max_duration"], str(spec.get("max_duration", "")))

    # ---- Actions ---------------------------------------------------------

    def _detect_package(self):
        package = get_foreground_package()
        self._set_entry(self.remote_folder_entry, f"/storage/emulated/0/Android/data/{package}/files/Camera1/" or "")
        if not package:
            show_toast(self.win, "Could not detect foreground app", fg_color="#d94040")
            return
        self.package_entry.delete(0, "end")
        self.package_entry.insert(0, package)
        show_toast(self.win, f"Detected: {package}")

    def _cancel(self):
        self.win.destroy()

    def _save(self):
        config, errors = self._build_and_validate()
        if errors:
            self._show_errors(errors)
            return

        platforms_file = get_platforms_file()
        if not platforms_file:
            show_toast(self.win, "platforms.json not found", fg_color="#d94040", duration=3500)
            return

        try:
            with open(platforms_file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Could not read platforms.json: {e}")
            show_toast(self.win, "Could not read platforms.json", fg_color="#d94040", duration=3500)
            return

        if "platforms" not in data or not isinstance(data["platforms"], list):
            show_toast(self.win, "platforms.json has unexpected structure", fg_color="#d94040", duration=3500)
            return

        # Backup before write
        backup_path = platforms_file + ".bak"
        try:
            shutil.copy2(platforms_file, backup_path)
            print(f"[+] Backed up platforms.json -> {backup_path}")
        except Exception as e:
            print(f"[ERROR] Backup failed: {e}")
            show_toast(self.win, "Backup failed, save aborted", fg_color="#d94040", duration=3500)
            return

        # Apply the change (subclasses decide append vs replace)
        try:
            self._apply_to_platforms_list(data["platforms"], config)
        except Exception as e:
            print(f"[ERROR] Could not apply change: {e}")
            show_toast(self.win, "Save failed", fg_color="#d94040", duration=3500)
            return

        try:
            with open(platforms_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Could not write platforms.json: {e}")
            try:
                shutil.copy2(backup_path, platforms_file)
                print("[+] Restored platforms.json from backup")
            except Exception as restore_err:
                print(f"[ERROR] Restore from backup also failed: {restore_err}")
            show_toast(self.win, "Save failed", fg_color="#d94040", duration=3500)
            return

        action = "Updated" if self._edit_index is not None else "Added"
        print(f"[+] {action} platform: {config['name']} ({config['package_name']})")
        self.result_saved = True
        if self.on_saved:
            try:
                self.on_saved(config)
            except Exception as e:
                print(f"[ERROR] on_saved callback failed: {e}")
        show_toast(self.parent, f"Platform '{config['name']}' {action.lower()}")
        self.win.destroy()

    def _apply_to_platforms_list(self, platforms_list, config):
        """Override in subclass — decides append vs replace."""
        raise NotImplementedError

    # ---- Validation ------------------------------------------------------

    def _build_and_validate(self):
        """Returns (config_dict_or_None, errors_list)."""
        errors = []

        name = self.name_entry.get().strip()
        package = self.package_entry.get().strip()
        photo_mode = self.photo_mode_var.get()

        if not name:
            errors.append("Platform name is required.")
        if not package:
            errors.append("Package name is required.")
        elif not PACKAGE_NAME_RE.match(package):
            errors.append(
                "Package name must look like 'com.example.app' "
                "(lowercase, dot-separated, at least two segments)."
            )

        # Duplicate check — skip the platform being edited (self-collision)
        for idx, existing in enumerate(self.existing_platforms):
            if idx == self._edit_index:
                continue
            if name and existing.get("name", "").lower() == name.lower():
                errors.append(f"A platform named '{name}' already exists.")
                break
        for idx, existing in enumerate(self.existing_platforms):
            if idx == self._edit_index:
                continue
            if package and existing.get("package_name") == package:
                errors.append(f"A platform with package '{package}' already exists.")
                break

        # Photo mode + paths
        if photo_mode == "gallery":
            gallery_path = self.gallery_path_entry.get().strip()
            if not gallery_path:
                errors.append("Gallery path is required for photo_mode 'gallery'.")
            elif not gallery_path.startswith("/"):
                errors.append("Gallery path must be an absolute Android path (start with '/').")
            elif not gallery_path.endswith("/"):
                errors.append("Gallery path must end with '/'.")
            remote_folder = f"/storage/emulated/0/Android/data/{package}/files/Camera1/" if package else ""
        else:  # vcam
            gallery_path = None
            remote_folder = self.remote_folder_entry.get().strip()
            if not remote_folder:
                errors.append("Remote folder is required for photo_mode 'vcam'.")
            elif not remote_folder.startswith("/"):
                errors.append("Remote folder must be an absolute Android path (start with '/').")
            elif not remote_folder.endswith("/"):
                errors.append("Remote folder must end with '/'.")



        photo, photo_errors = self._validate_specs(self.photo_widgets, "Photo", include_max_duration=False)
        errors.extend(photo_errors)
        video, video_errors = self._validate_specs(self.video_widgets, "Video", include_max_duration=True)
        errors.extend(video_errors)

        if errors:
            return None, errors

        config = {
            "name": name,
            "package_name": package,
            "remote_folder": remote_folder,
            "photo_mode": photo_mode,
            "gallery_path": gallery_path,
            "photo": photo,
            "video": video,
        }
        return config, []

    def _validate_specs(self, widgets, label, include_max_duration):
        errors = []
        spec = {}

        for key in ("width", "height"):
            raw = widgets[key].get().strip()
            if not raw:
                errors.append(f"{label} {key} is required.")
                continue
            try:
                value = int(raw)
                if value <= 0:
                    errors.append(f"{label} {key} must be a positive integer.")
                    continue
                spec[key] = value
            except ValueError:
                errors.append(f"{label} {key} must be a whole number.")

        raw_rotate = widgets["rotate"].get().strip()
        if raw_rotate == "":
            spec["rotate"] = None
        else:
            try:
                rotate_val = int(raw_rotate)
                if rotate_val not in (0, 90, 180, 270):
                    errors.append(f"{label} rotate must be 0, 90, 180, 270, or blank.")
                else:
                    spec["rotate"] = rotate_val
            except ValueError:
                errors.append(f"{label} rotate must be a whole number or blank.")

        raw_mirror = widgets["mirror"].get().strip().lower()
        if raw_mirror == "true":
            spec["mirror"] = True
        elif raw_mirror == "false":
            spec["mirror"] = False
        elif raw_mirror == "":
            spec["mirror"] = None
        else:
            errors.append(f"{label} mirror must be true or false.")

        raw_resize = widgets["resize_mode"].get().strip()
        if raw_resize not in RESIZE_MODES:
            errors.append(f"{label} resize mode must be one of {', '.join(RESIZE_MODES)}.")
        else:
            spec["resize_mode"] = raw_resize

        raw_filename = widgets["filename"].get().strip()
        if not raw_filename:
            errors.append(f"{label} filename is required.")
        elif "/" in raw_filename or "\\" in raw_filename:
            errors.append(f"{label} filename must not contain slashes.")
        else:
            spec["filename"] = raw_filename

        if include_max_duration:
            raw_dur = widgets["max_duration"].get().strip()
            if not raw_dur:
                errors.append(f"{label} max duration is required.")
            else:
                try:
                    dur = int(raw_dur)
                    if dur <= 0:
                        errors.append(f"{label} max duration must be a positive integer.")
                    else:
                        spec["max_duration"] = dur
                except ValueError:
                    errors.append(f"{label} max duration must be a whole number.")

        return spec, errors

    def _show_errors(self, errors):
        popup = ctk.CTkToplevel(self.win)
        popup.title("Validation errors")
        popup.geometry("500x400")
        popup.transient(self.win)
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text="Please fix the following before saving:",
            font=("Arial", 13, "bold"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        text_box = ctk.CTkTextbox(popup, wrap="word")
        text_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        text_box.insert("1.0", "\n".join(f"• {e}" for e in errors))
        text_box.configure(state="disabled")

        ctk.CTkButton(
            popup,
            text="OK",
            width=100,
            command=popup.destroy,
        ).pack(pady=(0, 12))


# ============================================================================
# Add wizard — appends a new platform
# ============================================================================

class PlatformWizard(_PlatformFormBase):
    """
    Modal dialog for adding a new platform to platforms.json.
    Strict validation, backup before write, blocks duplicates.
    """

    WINDOW_TITLE = "Add New Platform"
    SAVE_BUTTON_LABEL = "Save platform"
    HEADER_TITLE = "Add New Platform"
    HEADER_SUBTITLE = "Fill in all fields. The wizard validates everything before saving."

    def _apply_to_platforms_list(self, platforms_list, config):
        platforms_list.append(config)


# ============================================================================
# Edit dialog — replaces an existing platform in place
# ============================================================================

class PlatformEditor(_PlatformFormBase):
    """
    Modal dialog for editing an existing platform. Officer picks which
    platform to edit from a dropdown; the form pre-fills from that entry
    and writes back in place. Cannot add or delete — edit only.
    """

    WINDOW_TITLE = "Manage Platforms"
    SAVE_BUTTON_LABEL = "Save changes"
    HEADER_TITLE = "Manage Platforms"
    HEADER_SUBTITLE = "Pick a platform to edit. Use 'Add Platform' on the toolbar to create new ones."

    @classmethod
    def open(cls, parent, on_saved=None):
        """
        Factory: returns a new PlatformEditor or None if there's nothing to
        edit. Callers should use this rather than the constructor directly,
        because we can't bail cleanly out of __init__.
        """
        try:
            platforms = load_platforms()
        except Exception as e:
            print(f"[ERROR] Could not load platforms: {e}")
            platforms = []

        if not platforms:
            show_toast(parent, "No platforms to edit", fg_color="#d94040")
            return None

        return cls(parent, on_saved=on_saved)

    def __init__(self, parent, on_saved=None):
        super().__init__(parent, on_saved=on_saved)

        # Pre-fill from the first platform
        if self.existing_platforms:
            self._edit_index = 0
            self._populate_form_from_platform(self.existing_platforms[0])

    def _build_pre_form(self, scroll):
        """Add a platform-picker dropdown above the identity section."""
        self._section_label(scroll, "Pick a platform to edit")

        picker_block = ctk.CTkFrame(scroll, fg_color="transparent")
        picker_block.pack(fill="x", padx=4, pady=(0, 6))

        names = [p.get("name", "?") for p in self.existing_platforms] or ["(none)"]
        self.picker_combo = ctk.CTkComboBox(
            picker_block,
            values=names,
            command=self._on_platform_picked,
        )
        self.picker_combo.set(names[0])
        self.picker_combo.pack(fill="x")

    def _on_platform_picked(self, name):
        for idx, p in enumerate(self.existing_platforms):
            if p.get("name") == name:
                self._edit_index = idx
                self._populate_form_from_platform(p)
                return

    def _apply_to_platforms_list(self, platforms_list, config):
        """Replace the entry whose package_name matches the original."""
        original_pkg = self.existing_platforms[self._edit_index].get("package_name")
        for i, p in enumerate(platforms_list):
            if p.get("package_name") == original_pkg:
                platforms_list[i] = config
                return
        # Couldn't find it — fall back to append rather than silently lose data
        print(f"[!] Original platform '{original_pkg}' not found in file, appending instead")
        platforms_list.append(config)

# stdlib
# (none)

# third-party
import customtkinter as ctk

# internal
# (none)


# ============================================================================
# Translation strings
# ============================================================================
# Keys are short, stable identifiers. English is the reference language —
# when adding a key, add it to BOTH dicts. f-string-style placeholders use
# str.format syntax, e.g. t("found_media", count=5).
#
# print() debug logs and symbol-only labels (⏺ ☰ ⌂ ▶ 🎬) are intentionally
# NOT translated and do not appear here.

EN = {
    # ── App / window titles ──
    "app_window_title": "ADB Media Manager",
    "app_window_title_session": "ADB Media Manager — {officer} — Case {case}",

    # ── Language picker ──
    "lang_picker_title": "Language / Taal",
    "lang_picker_heading": "Select a language",
    "lang_picker_english": "English",
    "lang_picker_dutch": "Nederlands",

    # ── Login screen (case_manager) ──
    "login_window_title": "Officer Login",
    "login_heading": "SMMPI - Officer Login",
    "login_name_label": "Name:",
    "login_name_placeholder": "Enter your name",
    "login_error_no_name": "Please enter your name",
    "btn_continue": "Continue",
    "btn_cancel": "Cancel",

    # ── Case selection (case_manager) ──
    "case_window_title": "Select Case",
    "case_welcome": "Welcome, {officer}",
    "case_subtitle": "Select an existing case or create a new one",
    "case_folder_label": "Case folder: {path}",
    "btn_change": "Change",
    "case_root_dialog_title": "Select Case Root Folder",
    "case_save_root_failed": "Could not save new case folder. Check folder permissions and try again.",
    "case_new_placeholder": "Enter new case number",
    "btn_new_case": "New Case",
    "case_error_no_number": "Please enter a case number",
    "case_error_invalid_chars": "Case number may only contain letters, digits, hyphens, underscores",
    "case_existing_heading": "Existing Cases",
    "case_none_found": "No cases found. Create a new case to get started.",
    "case_file_count": "  {name}\n  {count} file(s)",

    # ── Topbar / sidebar (ui_setup) ──
    "no_active_session": "No active session",
    "session_label": "Officer: {officer}  |  Case: {case}",
    "btn_about": "About",
    "sidebar_new_case": "New Case",
    "sidebar_switch_case": "Switch Case",
    "sidebar_platforms": "PLATFORMS",
    "sidebar_add_platform": "+ Add Platform",
    "sidebar_manage_platforms": "Manage Platforms",

    # ── Left / middle / right panels (ui_setup) ──
    "btn_select_folder": "Select Folder",
    "no_folder_selected": "No folder selected",
    "select_folder_prompt": "Select a folder to display images and videos",
    "btn_confirm_selection": "Confirm Selection",
    "device_screen": "Device Screen",
    "tooltip_start_recording": "Start Recording",
    "tooltip_close_app": "Close Foreground App",

    # ── About popup (ui_setup) ──
    "about_window_title": "About ADB Media Manager",
    "about_version": "Version: {version}",
    "about_build": "Build: {build}",
    "about_release_notes": "Release notes",
    "btn_close": "Close",

    # ── Folder selector ──
    "folder_dialog_title": "Select a Folder Containing Images and Videos",

    # ── Main app: case change / session ──
    "toast_stop_recording_first": "Stop the recording before changing case",
    "new_case_selected": "New case selected",
    "case_changed": "Case changed",
    "toast_case_changed": "{message}: {case}",

    # ── Main app: stream / device ──
    "no_device_connected": "No device connected",
    "stream_already_running": "Stream already running",
    "streaming_started": "Streaming started",
    "error_generic": "Error: {error}",
    "connected_device": "Connected: {manufacturer} {model}",
    "connected_serial": "Connected: {serial}",
    "device_disconnected": "Device disconnected",
    "stream_stopped_disconnected": "Stream stopped - device disconnected",
    "toast_device_disconnected": "Device disconnected - reconnect to continue",

    # ── Main app: platform detection ──
    "detecting_platform_attempt": "Detecting platform... (attempt {attempt}/{attempts})",
    "detecting_active_platform": "Detecting active platform...",
    "no_supported_platform": "No supported platform detected.",
    "found_media": "Found {count} media files",
    "no_media_in_folder": "No media files found in selected folder",
    "path_label": "Path: {path}",
    "selected_file": "Selected: {filename}",
    "no_file_selected": "No file selected",
    "unsupported_file_type": "Unsupported file type: {ext}",

    # ── Main app: login required gates ──
    "login_required_add": "Login required to add platforms",
    "login_required_manage": "Login required to manage platforms",

    # ── Main app: unknown platform popup ──
    "unknown_platform_title": "Platform Not Recognised",
    "unknown_platform_heading": "No supported platform detected.",
    "unknown_platform_body": "Open Snapchat or WhatsApp on the phone,\nmake sure it is in the foreground,\nthen try again.",
    "btn_ok": "OK",

    # ── Main app: close-while-recording popup ──
    "close_recording_title": "Recording in progress",
    "close_recording_heading": "⚠  A recording is still running",
    "close_recording_body": "Closing the app now can corrupt the video file.\nStop the recording first so it can be saved properly.",
    "btn_stop_and_close": "Stop recording & close",
    "btn_keep_recording": "Keep recording",
    "btn_force_close": "Force close (video will be lost)",

    # ── Main app: recording flow ──
    "recording_already_stopping": "Recording is already stopping...",
    "stopping_recording": "Stopping recording...",
    "recording_still_saving": "Recording is still saving. Please wait.",
    "recording_still_saving_short": "Recording is still saving...",
    "no_active_case_session": "No active case session.",
    "recording_started": "Recording started",
    "recording_saved": "Recording saved",
    "recording_saved_success": "Recording saved successfully",
    "recording_failed_start": "Recording failed to start",
    "stopping_before_close": "Stopping recording before closing...",
    "recording_error": "Recording error: {error}",
    "recording_stop_failed_label": "Recording stop failed - check temp MKV file",
    "recording_stop_failed_toast": "Recording stop failed - check the case folder for the .mkv temp file",
    "recording_stop_failed_kept_open": "Recording stop failed - app kept open for safety",
    "recovered_recordings": "Recovered {count} unfinished recording(s)",
    "window_resize_disabled": "Window resizing is disabled while recording",

    # ── Main app: foreground app close ──
    "no_platform_foreground": "No supported platform in foreground",
    "platform_closed": "{platform} closed",
    "failed_close_app": "Failed to close app",

    # ── Device manager ──
    "device_window_title": "Select Android Device",
    "device_heading": "Connect Android Device",
    "device_instructions": "Make sure USB debugging is enabled on your device\nand it's connected via USB.",
    "btn_refresh_devices": "Refresh Devices",
    "device_scan_prompt": "Click 'Refresh Devices' to scan for devices",
    "btn_connect": "Connect",
    "device_none_found": "No devices found. Check USB debugging and connection.",
    "device_found_count": "Found {count} device(s). Select one to continue.",
    "device_entry": "{manufacturer} {model}\nSerial: {serial}",
    "device_error_scan": "Error scanning devices: {error}",
    "device_selected": "✓ Selected: {name}.",
    "device_select_first": "Please select a device first",

    # ── Image to video / push (image_to_video) ──
    "resizing_image": "Resizing image ({mode})...",
    "failed_resize_image": "Failed to resize image",
    "pushing_image_gallery": "Pushing image to device gallery...",
    "failed_push_image": "Failed to push image to device — check USB connection and device authorization",
    "failed_push_video": "Failed to push video to device — check USB connection, device authorization, and that the target app has been opened at least once",
    "image_pushed_gallery": "Image pushed to gallery. Use {platform} attach > Gallery to send it.",
    "image_sent_success": "Image sent successfully",
    "converting_image_video": "Converting image to video ({width}x{height})...",
    "failed_convert_image_video": "Failed to convert image to video",
    "pushing_video": "Pushing video to device...",
    "video_pushed": "Successfully pushed {filename} ({width}x{height}) to device",
    "no_platform_foreground_detected": "No supported platform detected in foreground",

    # ── Video (video.py) ──
    "no_supported_platform_short": "No supported platform detected",
    "video_too_long": "Video too long ({duration:.1f}s). Max is {max}s.",
    "converting_video": "Converting video ({duration:.1f}s) for {platform} ({width}x{height})...",
    "failed_convert_video": "Failed to convert video",
    "restarting_platform": "Restarting {platform}...",
    "video_done": "Done — pushed virtual.mp4 to {platform} ({duration:.1f}s, {width}x{height})",

    # ── Image display (image_display) ──
    "error_loading_image": "Error loading image:\n{error}",
    "video_file_placeholder": "Video File\n{name}\n(Video)",
    "video_thumb_failed": "Video File\n{name}\n\n(Thumbnail extraction failed)",
    "error_placeholder": "Error\n{name}\n(Error)",

    # ── Platform wizard — shared ──
    "wiz_default_window_title": "Platform",
    "wiz_default_save": "Save",
    "wiz_default_header": "Platform",
    "wiz_section_identity": "Platform identity",
    "wiz_name_label": "Platform name (e.g. Instagram)",
    "wiz_package_label": "Package name (e.g. com.instagram.android)",
    "wiz_btn_detect": "Detect from phone",
    "wiz_detect_hint": "Open the target app on the phone and bring it to the foreground, then click Detect.",
    "wiz_section_photo_method": "Photo delivery method",
    "wiz_photo_method_hint": "gallery — push photo to phone gallery (works for apps with hardened cameras like WhatsApp/Discord)\nvcam — feed photo through the virtual camera (Snapchat-style)",
    "wiz_gallery_path_label": "Gallery path on phone",
    "wiz_remote_folder_label": "Remote folder (the folder VCAM watches on the phone)",
    "wiz_section_photo_specs": "Photo specs",
    "wiz_section_video_specs": "Video specs",
    "wiz_spec_width": "Width",
    "wiz_spec_height": "Height",
    "wiz_spec_rotate": "Rotate (0/90/180/270, blank = none)",
    "wiz_spec_mirror": "Mirror",
    "wiz_spec_resize": "Resize mode",
    "wiz_spec_filename": "Filename",
    "wiz_spec_max_duration": "Max duration (seconds)",
    "wiz_section_pick_edit": "Pick a platform to edit",
    "wiz_picker_none": "(none)",

    # ── Platform wizard — labels used in validation messages ──
    "wiz_label_photo": "Photo",
    "wiz_label_video": "Video",
    "wiz_field_width": "width",
    "wiz_field_height": "height",

    # ── Platform wizard — validation errors ──
    "wiz_err_name_required": "Platform name is required.",
    "wiz_err_package_required": "Package name is required.",
    "wiz_err_package_format": "Package name must look like 'com.example.app' (lowercase, dot-separated, at least two segments).",
    "wiz_err_name_exists": "A platform named '{name}' already exists.",
    "wiz_err_package_exists": "A platform with package '{package}' already exists.",
    "wiz_err_gallery_required": "Gallery path is required for photo_mode 'gallery'.",
    "wiz_err_gallery_absolute": "Gallery path must be an absolute Android path (start with '/').",
    "wiz_err_gallery_trailing": "Gallery path must end with '/'.",
    "wiz_err_remote_required": "Remote folder is required for photo_mode 'vcam'.",
    "wiz_err_remote_absolute": "Remote folder must be an absolute Android path (start with '/').",
    "wiz_err_remote_trailing": "Remote folder must end with '/'.",
    "wiz_err_field_required": "{label} {field} is required.",
    "wiz_err_field_positive": "{label} {field} must be a positive integer.",
    "wiz_err_field_whole": "{label} {field} must be a whole number.",
    "wiz_err_rotate_value": "{label} rotate must be 0, 90, 180, 270, or blank.",
    "wiz_err_rotate_whole": "{label} rotate must be a whole number or blank.",
    "wiz_err_mirror_bool": "{label} mirror must be true or false.",
    "wiz_err_resize_mode": "{label} resize mode must be one of {modes}.",
    "wiz_err_filename_required": "{label} filename is required.",
    "wiz_err_filename_slashes": "{label} filename must not contain slashes.",
    "wiz_err_duration_required": "{label} max duration is required.",
    "wiz_err_duration_positive": "{label} max duration must be a positive integer.",
    "wiz_err_duration_whole": "{label} max duration must be a whole number.",

    # ── Platform wizard — error popup + save flow ──
    "wiz_errors_title": "Validation errors",
    "wiz_errors_heading": "Please fix the following before saving:",
    "wiz_add_window_title": "Add New Platform",
    "wiz_add_save": "Save platform",
    "wiz_add_header": "Add New Platform",
    "wiz_add_subtitle": "Fill in all fields. The wizard validates everything before saving.",
    "wiz_edit_window_title": "Manage Platforms",
    "wiz_edit_save": "Save changes",
    "wiz_edit_header": "Manage Platforms",
    "wiz_edit_subtitle": "Pick a platform to edit. Use 'Add Platform' on the toolbar to create new ones.",
    "wiz_no_platforms_edit": "No platforms to edit",
    "wiz_detect_failed": "Could not detect foreground app",
    "wiz_detected": "Detected: {package}",
    "wiz_file_not_found": "platforms.json not found",
    "wiz_read_failed": "Could not read platforms.json",
    "wiz_bad_structure": "platforms.json has unexpected structure",
    "wiz_backup_failed": "Backup failed, save aborted",
    "wiz_save_failed": "Save failed",
    "wiz_saved_added": "Platform '{name}' added",
    "wiz_saved_updated": "Platform '{name}' updated",
}

NL = {
    # ── App / window titles ──
    "app_window_title": "ADB Media Manager",
    "app_window_title_session": "ADB Media Manager — {officer} — Zaak {case}",

    # ── Language picker ──
    "lang_picker_title": "Language / Taal",
    "lang_picker_heading": "Kies een taal",
    "lang_picker_english": "English",
    "lang_picker_dutch": "Nederlands",

    # ── Login screen (case_manager) ──
    "login_window_title": "Inloggen rechercheur",
    "login_heading": "SMMPI - Inloggen rechercheur",
    "login_name_label": "Naam:",
    "login_name_placeholder": "Voer je naam in",
    "login_error_no_name": "Voer je naam in",
    "btn_continue": "Doorgaan",
    "btn_cancel": "Annuleren",

    # ── Case selection (case_manager) ──
    "case_window_title": "Zaak selecteren",
    "case_welcome": "Welkom, {officer}",
    "case_subtitle": "Selecteer een bestaande zaak of maak een nieuwe aan",
    "case_folder_label": "Zaakmap: {path}",
    "btn_change": "Wijzigen",
    "case_root_dialog_title": "Selecteer hoofdmap voor zaken",
    "case_save_root_failed": "Kon de nieuwe zaakmap niet opslaan. Controleer de mapmachtigingen en probeer het opnieuw.",
    "case_new_placeholder": "Voer een nieuw zaaknummer in",
    "btn_new_case": "Nieuwe zaak",
    "case_error_no_number": "Voer een zaaknummer in",
    "case_error_invalid_chars": "Een zaaknummer mag alleen letters, cijfers, koppeltekens en underscores bevatten",
    "case_existing_heading": "Bestaande zaken",
    "case_none_found": "Geen zaken gevonden. Maak een nieuwe zaak aan om te beginnen.",
    "case_file_count": "  {name}\n  {count} bestand(en)",

    # ── Topbar / sidebar (ui_setup) ──
    "no_active_session": "Geen actieve sessie",
    "session_label": "Rechercheur: {officer}  |  Zaak: {case}",
    "btn_about": "Over",
    "sidebar_new_case": "Nieuwe zaak",
    "sidebar_switch_case": "Zaak wisselen",
    "sidebar_platforms": "PLATFORMS",
    "sidebar_add_platform": "+ Platform toevoegen",
    "sidebar_manage_platforms": "Platforms beheren",

    # ── Left / middle / right panels (ui_setup) ──
    "btn_select_folder": "Map selecteren",
    "no_folder_selected": "Geen map geselecteerd",
    "select_folder_prompt": "Selecteer een map om afbeeldingen en video's te tonen",
    "btn_confirm_selection": "Selectie bevestigen",
    "device_screen": "Apparaatscherm",
    "tooltip_start_recording": "Opname starten",
    "tooltip_close_app": "App op voorgrond sluiten",

    # ── About popup (ui_setup) ──
    "about_window_title": "Over ADB Media Manager",
    "about_version": "Versie: {version}",
    "about_build": "Build: {build}",
    "about_release_notes": "Release-opmerkingen",
    "btn_close": "Sluiten",

    # ── Folder selector ──
    "folder_dialog_title": "Selecteer een map met afbeeldingen en video's",

    # ── Main app: case change / session ──
    "toast_stop_recording_first": "Stop de opname voordat je van zaak wisselt",
    "new_case_selected": "Nieuwe zaak geselecteerd",
    "case_changed": "Zaak gewijzigd",
    "toast_case_changed": "{message}: {case}",

    # ── Main app: stream / device ──
    "no_device_connected": "Geen apparaat verbonden",
    "stream_already_running": "Stream is al actief",
    "streaming_started": "Streamen gestart",
    "error_generic": "Fout: {error}",
    "connected_device": "Verbonden: {manufacturer} {model}",
    "connected_serial": "Verbonden: {serial}",
    "device_disconnected": "Apparaat losgekoppeld",
    "stream_stopped_disconnected": "Stream gestopt - apparaat losgekoppeld",
    "toast_device_disconnected": "Apparaat losgekoppeld - verbind opnieuw om door te gaan",

    # ── Main app: platform detection ──
    "detecting_platform_attempt": "Platform detecteren... (poging {attempt}/{attempts})",
    "detecting_active_platform": "Actief platform detecteren...",
    "no_supported_platform": "Geen ondersteund platform gedetecteerd.",
    "found_media": "{count} mediabestanden gevonden",
    "no_media_in_folder": "Geen mediabestanden gevonden in de geselecteerde map",
    "path_label": "Pad: {path}",
    "selected_file": "Geselecteerd: {filename}",
    "no_file_selected": "Geen bestand geselecteerd",
    "unsupported_file_type": "Niet-ondersteund bestandstype: {ext}",

    # ── Main app: login required gates ──
    "login_required_add": "Inloggen vereist om platforms toe te voegen",
    "login_required_manage": "Inloggen vereist om platforms te beheren",

    # ── Main app: unknown platform popup ──
    "unknown_platform_title": "Platform niet herkend",
    "unknown_platform_heading": "Geen ondersteund platform gedetecteerd.",
    "unknown_platform_body": "Open Snapchat of WhatsApp op de telefoon,\nzorg dat het op de voorgrond staat,\nen probeer het opnieuw.",
    "btn_ok": "OK",

    # ── Main app: close-while-recording popup ──
    "close_recording_title": "Opname bezig",
    "close_recording_heading": "⚠  Er is nog een opname actief",
    "close_recording_body": "De app nu sluiten kan het videobestand beschadigen.\nStop eerst de opname zodat deze goed wordt opgeslagen.",
    "btn_stop_and_close": "Opname stoppen & sluiten",
    "btn_keep_recording": "Opname behouden",
    "btn_force_close": "Geforceerd sluiten (video gaat verloren)",

    # ── Main app: recording flow ──
    "recording_already_stopping": "Opname is al aan het stoppen...",
    "stopping_recording": "Opname stoppen...",
    "recording_still_saving": "Opname wordt nog opgeslagen. Even geduld.",
    "recording_still_saving_short": "Opname wordt nog opgeslagen...",
    "no_active_case_session": "Geen actieve zaaksessie.",
    "recording_started": "Opname gestart",
    "recording_saved": "Opname opgeslagen",
    "recording_saved_success": "Opname succesvol opgeslagen",
    "recording_failed_start": "Opname kon niet starten",
    "stopping_before_close": "Opname stoppen voor het sluiten...",
    "recording_error": "Opnamefout: {error}",
    "recording_stop_failed_label": "Stoppen van opname mislukt - controleer tijdelijk MKV-bestand",
    "recording_stop_failed_toast": "Stoppen van opname mislukt - controleer de zaakmap op het tijdelijke .mkv-bestand",
    "recording_stop_failed_kept_open": "Stoppen van opname mislukt - app blijft open voor de veiligheid",
    "recovered_recordings": "{count} onafgemaakte opname(s) hersteld",
    "window_resize_disabled": "Venstergrootte aanpassen is uitgeschakeld tijdens opname",

    # ── Main app: foreground app close ──
    "no_platform_foreground": "Geen ondersteund platform op de voorgrond",
    "platform_closed": "{platform} gesloten",
    "failed_close_app": "App sluiten mislukt",

    # ── Device manager ──
    "device_window_title": "Android-apparaat selecteren",
    "device_heading": "Android-apparaat verbinden",
    "device_instructions": "Zorg dat USB-foutopsporing is ingeschakeld op je apparaat\nen dat het via USB is verbonden.",
    "btn_refresh_devices": "Apparaten vernieuwen",
    "device_scan_prompt": "Klik op 'Apparaten vernieuwen' om te zoeken naar apparaten",
    "btn_connect": "Verbinden",
    "device_none_found": "Geen apparaten gevonden. Controleer USB-foutopsporing en verbinding.",
    "device_found_count": "{count} apparaat/apparaten gevonden. Selecteer er een om door te gaan.",
    "device_entry": "{manufacturer} {model}\nSerienummer: {serial}",
    "device_error_scan": "Fout bij het zoeken naar apparaten: {error}",
    "device_selected": "✓ Geselecteerd: {name}.",
    "device_select_first": "Selecteer eerst een apparaat",

    # ── Image to video / push (image_to_video) ──
    "resizing_image": "Afbeelding schalen ({mode})...",
    "failed_resize_image": "Schalen van afbeelding mislukt",
    "pushing_image_gallery": "Afbeelding naar galerij van apparaat pushen...",
    "failed_push_image": "Afbeelding pushen naar apparaat mislukt — controleer USB-verbinding en apparaatautorisatie",
    "failed_push_video": "Video pushen naar apparaat mislukt — controleer USB-verbinding, apparaatautorisatie en of de doel-app minstens één keer is geopend",
    "image_pushed_gallery": "Afbeelding naar galerij gepusht. Gebruik {platform} bijlage > Galerij om te versturen.",
    "image_sent_success": "Afbeelding succesvol verzonden",
    "converting_image_video": "Afbeelding naar video converteren ({width}x{height})...",
    "failed_convert_image_video": "Converteren van afbeelding naar video mislukt",
    "pushing_video": "Video naar apparaat pushen...",
    "video_pushed": "{filename} ({width}x{height}) succesvol naar apparaat gepusht",
    "no_platform_foreground_detected": "Geen ondersteund platform op de voorgrond gedetecteerd",

    # ── Video (video.py) ──
    "no_supported_platform_short": "Geen ondersteund platform gedetecteerd",
    "video_too_long": "Video te lang ({duration:.1f}s). Max is {max}s.",
    "converting_video": "Video converteren ({duration:.1f}s) voor {platform} ({width}x{height})...",
    "failed_convert_video": "Converteren van video mislukt",
    "restarting_platform": "{platform} herstarten...",
    "video_done": "Klaar — virtual.mp4 naar {platform} gepusht ({duration:.1f}s, {width}x{height})",

    # ── Image display (image_display) ──
    "error_loading_image": "Fout bij laden van afbeelding:\n{error}",
    "video_file_placeholder": "Videobestand\n{name}\n(Video)",
    "video_thumb_failed": "Videobestand\n{name}\n\n(Thumbnail-extractie mislukt)",
    "error_placeholder": "Fout\n{name}\n(Fout)",

    # ── Platform wizard — shared ──
    "wiz_default_window_title": "Platform",
    "wiz_default_save": "Opslaan",
    "wiz_default_header": "Platform",
    "wiz_section_identity": "Platformidentiteit",
    "wiz_name_label": "Platformnaam (bijv. Instagram)",
    "wiz_package_label": "Pakketnaam (bijv. com.instagram.android)",
    "wiz_btn_detect": "Detecteren van telefoon",
    "wiz_detect_hint": "Open de doel-app op de telefoon en breng deze naar de voorgrond, klik dan op Detecteren.",
    "wiz_section_photo_method": "Foto-afleveringsmethode",
    "wiz_photo_method_hint": "gallery — foto naar telefoongalerij pushen (werkt voor apps met geharde camera's zoals WhatsApp/Discord)\nvcam — foto via de virtuele camera doorgeven (Snapchat-stijl)",
    "wiz_gallery_path_label": "Galerijpad op telefoon",
    "wiz_remote_folder_label": "Externe map (de map die VCAM op de telefoon bekijkt)",
    "wiz_section_photo_specs": "Fotospecificaties",
    "wiz_section_video_specs": "Videospecificaties",
    "wiz_spec_width": "Breedte",
    "wiz_spec_height": "Hoogte",
    "wiz_spec_rotate": "Roteren (0/90/180/270, leeg = geen)",
    "wiz_spec_mirror": "Spiegelen",
    "wiz_spec_resize": "Schaalmodus",
    "wiz_spec_filename": "Bestandsnaam",
    "wiz_spec_max_duration": "Maximale duur (seconden)",
    "wiz_section_pick_edit": "Kies een platform om te bewerken",
    "wiz_picker_none": "(geen)",

    # ── Platform wizard — labels used in validation messages ──
    "wiz_label_photo": "Foto",
    "wiz_label_video": "Video",
    "wiz_field_width": "breedte",
    "wiz_field_height": "hoogte",

    # ── Platform wizard — validation errors ──
    "wiz_err_name_required": "Platformnaam is verplicht.",
    "wiz_err_package_required": "Pakketnaam is verplicht.",
    "wiz_err_package_format": "Pakketnaam moet eruitzien als 'com.example.app' (kleine letters, gescheiden door punten, minstens twee segmenten).",
    "wiz_err_name_exists": "Een platform met de naam '{name}' bestaat al.",
    "wiz_err_package_exists": "Een platform met pakket '{package}' bestaat al.",
    "wiz_err_gallery_required": "Galerijpad is verplicht voor photo_mode 'gallery'.",
    "wiz_err_gallery_absolute": "Galerijpad moet een absoluut Android-pad zijn (beginnen met '/').",
    "wiz_err_gallery_trailing": "Galerijpad moet eindigen op '/'.",
    "wiz_err_remote_required": "Externe map is verplicht voor photo_mode 'vcam'.",
    "wiz_err_remote_absolute": "Externe map moet een absoluut Android-pad zijn (beginnen met '/').",
    "wiz_err_remote_trailing": "Externe map moet eindigen op '/'.",
    "wiz_err_field_required": "{label} {field} is verplicht.",
    "wiz_err_field_positive": "{label} {field} moet een positief geheel getal zijn.",
    "wiz_err_field_whole": "{label} {field} moet een geheel getal zijn.",
    "wiz_err_rotate_value": "{label} roteren moet 0, 90, 180, 270 of leeg zijn.",
    "wiz_err_rotate_whole": "{label} roteren moet een geheel getal of leeg zijn.",
    "wiz_err_mirror_bool": "{label} spiegelen moet true of false zijn.",
    "wiz_err_resize_mode": "{label} schaalmodus moet een van {modes} zijn.",
    "wiz_err_filename_required": "{label} bestandsnaam is verplicht.",
    "wiz_err_filename_slashes": "{label} bestandsnaam mag geen schuine strepen bevatten.",
    "wiz_err_duration_required": "{label} maximale duur is verplicht.",
    "wiz_err_duration_positive": "{label} maximale duur moet een positief geheel getal zijn.",
    "wiz_err_duration_whole": "{label} maximale duur moet een geheel getal zijn.",

    # ── Platform wizard — error popup + save flow ──
    "wiz_errors_title": "Validatiefouten",
    "wiz_errors_heading": "Los het volgende op voor het opslaan:",
    "wiz_add_window_title": "Nieuw platform toevoegen",
    "wiz_add_save": "Platform opslaan",
    "wiz_add_header": "Nieuw platform toevoegen",
    "wiz_add_subtitle": "Vul alle velden in. De wizard valideert alles voor het opslaan.",
    "wiz_edit_window_title": "Platforms beheren",
    "wiz_edit_save": "Wijzigingen opslaan",
    "wiz_edit_header": "Platforms beheren",
    "wiz_edit_subtitle": "Kies een platform om te bewerken. Gebruik 'Platform toevoegen' op de werkbalk om nieuwe aan te maken.",
    "wiz_no_platforms_edit": "Geen platforms om te bewerken",
    "wiz_detect_failed": "Kon app op voorgrond niet detecteren",
    "wiz_detected": "Gedetecteerd: {package}",
    "wiz_file_not_found": "platforms.json niet gevonden",
    "wiz_read_failed": "Kon platforms.json niet lezen",
    "wiz_bad_structure": "platforms.json heeft een onverwachte structuur",
    "wiz_backup_failed": "Back-up mislukt, opslaan afgebroken",
    "wiz_save_failed": "Opslaan mislukt",
    "wiz_saved_added": "Platform '{name}' toegevoegd",
    "wiz_saved_updated": "Platform '{name}' bijgewerkt",
}


# ============================================================================
# Active-language state + lookup
# ============================================================================

_LANGUAGES = {"en": EN, "nl": NL}

# Default until the picker sets it. English is the safe fallback.
_active_code = "en"
_active = EN


def set_language(code):
    """Set the active language. Falls back to English on an unknown code."""
    global _active_code, _active
    if code not in _LANGUAGES:
        print(f"[WARN] Unknown language code '{code}', falling back to English")
        code = "en"
    _active_code = code
    _active = _LANGUAGES[code]


def get_language():
    """Return the active language code ('en' or 'nl')."""
    return _active_code


def t(key, **kwargs):
    """
    Look up a string by key in the active language and format it with kwargs.

    Falls back to English if the key is missing from the active language,
    and to the raw key if it's missing everywhere — so a missing translation
    degrades to visible-but-usable rather than crashing.
    """
    template = _active.get(key)
    if template is None:
        template = EN.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            # Bad/missing placeholder — return the unformatted template
            # rather than raising in the middle of building the UI.
            return template
    return template


# ============================================================================
# Language picker dialog
# ============================================================================

def show_language_picker(parent):
    """
    Show a small modal asking the user to pick English or Dutch.
    Blocks until a choice is made, sets the active language, and returns
    the chosen code. Defaults to English if the window is closed with X.

    Must be called before any translated UI is shown to the user.
    """
    choice = {"code": "en"}

    win = ctk.CTkToplevel(parent)
    win.title(t("lang_picker_title"))
    win.geometry("360x220")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    win.geometry("+{}+{}".format(
        int(parent.winfo_screenwidth() / 2 - 180),
        int(parent.winfo_screenheight() / 2 - 110)
    ))

    heading = ctk.CTkLabel(
        win,
        text=t("lang_picker_heading"),
        font=("Arial", 18, "bold")
    )
    heading.pack(pady=(30, 20))

    button_frame = ctk.CTkFrame(win, fg_color="transparent")
    button_frame.pack(pady=10)

    def pick(code):
        choice["code"] = code
        set_language(code)
        win.destroy()

    english_button = ctk.CTkButton(
        button_frame,
        text=t("lang_picker_english"),
        command=lambda: pick("en"),
        font=("Arial", 14),
        width=140,
        height=44
    )
    english_button.pack(side="left", padx=10)

    dutch_button = ctk.CTkButton(
        button_frame,
        text=t("lang_picker_dutch"),
        command=lambda: pick("nl"),
        font=("Arial", 14),
        width=140,
        height=44
    )
    dutch_button.pack(side="left", padx=10)

    # X button defaults to English (already the default in `choice`)
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.wait_window()

    return choice["code"]

# stdlib
import os

# third-party
from customtkinter import filedialog

# internal
from lang import t


class FolderSelector:
    def __init__(self):
        self.media_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v',
            '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.opus', '.wma'
        }

    def get_media_files(self, folder_path):
        media_files = []
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file.lower())
                    if ext in self.media_extensions:
                        media_files.append(file_path)

        return sorted(media_files)

    def select_folder(self):
        print("Button clicked!")
        folder_path = filedialog.askdirectory(
            title=t("folder_dialog_title")
        )
        if not folder_path:
            print("No folder selected. Exiting.")
            return None, []

        print(f"Selected folder: {folder_path}")
        media_files = self.get_media_files(folder_path)
        print(f"Found {len(media_files)} media files")
        return folder_path, media_files
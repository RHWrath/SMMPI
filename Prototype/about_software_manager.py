import os
import sys
import json


class AboutSoftwareManager:
    @staticmethod
    def get_app_resource_path(filename: str) -> str | None:
        candidates = []

        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)

            candidates.extend([
                os.path.join(exe_dir, "_internal", filename),
                os.path.join(exe_dir, filename),
            ])

            if hasattr(sys, "_MEIPASS"):
                candidates.extend([
                    os.path.join(sys._MEIPASS, filename),
                    os.path.join(sys._MEIPASS, "_internal", filename),
                ])
        else:
            dev_root = os.path.dirname(os.path.abspath(__file__))

            candidates.extend([
                os.path.join(dev_root, filename),
                os.path.join(dev_root, "_internal", filename),
            ])

        for path in candidates:
            print(f"[ABOUT][PATH] Checking: {path}")

            if os.path.exists(path):
                print(f"[ABOUT][PATH] Found: {path}")
                return path

        print(f"[ABOUT][PATH] File not found: {filename}")
        return None

    @staticmethod
    def load_version_info() -> dict:
        default_info = {
            "app_name": "ADB-Media-Manager",
            "version": "Unknown",
            "build": "Unknown",
            "description": "No description available.",
            "raw": {}
        }

        version_path = AboutSoftwareManager.get_app_resource_path("version.json")

        if not version_path:
            return default_info

        try:
            with open(version_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            app_name = (
                data.get("name")
                or data.get("appName")
                or data.get("app_name")
                or default_info["app_name"]
            )

            version = (
                data.get("version")
                or data.get("appVersion")
                or data.get("app_version")
                or default_info["version"]
            )

            build = (
                data.get("build")
                or data.get("buildDate")
                or data.get("build_date")
                or data.get("date")
                or default_info["build"]
            )

            description = (
                data.get("description")
                or default_info["description"]
            )

            return {
                "app_name": app_name,
                "version": version,
                "build": build,
                "description": description,
                "raw": data
            }

        except Exception as e:
            print(f"[ABOUT][VERSION] Failed to read version.json: {e}")
            return default_info

    @staticmethod
    def load_release_notes() -> str:
        release_note_path = AboutSoftwareManager.get_app_resource_path("release_notes.txt")

        if not release_note_path:
            return "No release notes found."

        try:
            with open(release_note_path, "r", encoding="utf-8") as file:
                content = file.read().strip()

            return content if content else "Release notes file is empty."

        except UnicodeDecodeError:
            try:
                with open(release_note_path, "r", encoding="cp1252") as file:
                    content = file.read().strip()

                return content if content else "Release notes file is empty."

            except Exception as e:
                print(f"[ABOUT][RELEASE] Failed fallback read: {e}")
                return "Failed to read release notes."

        except Exception as e:
            print(f"[ABOUT][RELEASE] Failed to read release_note.txt: {e}")
            return "Failed to read release notes."
        
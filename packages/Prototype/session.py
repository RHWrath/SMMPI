import os
import re
from datetime import datetime


# Characters Windows forbids in filenames, plus control chars.
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Valid case numbers: letters, digits, hyphens, underscores only.
_VALID_CASE_NUMBER = re.compile(r'^[A-Za-z0-9_-]+$')


class Session:
    """Holds session state: officer name, active case, and paths."""

    def __init__(self, officer_name, case_number, case_root):
        # Officer name: must be non-blank, unsafe chars stripped.
        if officer_name is None or officer_name.strip() == "":
            raise ValueError("officer_name cannot be blank")
        sanitised_name = _UNSAFE_FILENAME_CHARS.sub("", officer_name).strip()
        if sanitised_name == "":
            # All chars were unsafe — nothing usable left.
            raise ValueError("officer_name contains no usable characters")

        # Case number: must be non-blank and match the allowed charset.
        if case_number is None or case_number.strip() == "":
            raise ValueError("case_number cannot be blank")
        trimmed_case = case_number.strip()
        if not _VALID_CASE_NUMBER.match(trimmed_case):
            raise ValueError(
                f"case_number '{case_number}' contains invalid characters "
                "(allowed: letters, digits, hyphens, underscores)"
            )

        self.officer_name = sanitised_name
        self.case_number = trimmed_case
        self.case_root = case_root
        self.case_path = os.path.join(case_root, trimmed_case)
        self.started_at = datetime.now()

    def get_evidence_filename(self, extension=".mp4"):
        """
        Generate the evidence filename for this session.
        Format: {date}_{time}_{officer_name}.mp4
        Example: 2026-04-20_14-32-05_Jan_de_Vries.mp4
        """
        date_str = self.started_at.strftime("%Y-%m-%d")
        time_str = self.started_at.strftime("%H-%M-%S")
        # Replace spaces with underscores for filename safety
        safe_name = self.officer_name.strip().replace(" ", "_")
        return f"{date_str}_{time_str}_{safe_name}{extension}"

    def get_evidence_path(self, extension=".mp4"):
        """Full path where the evidence file should be saved."""
        return os.path.join(self.case_path, self.get_evidence_filename(extension))

    def ensure_case_folder(self):
        """Create the case folder if it doesn't exist. Returns the path."""
        os.makedirs(self.case_path, exist_ok=True)
        return self.case_path
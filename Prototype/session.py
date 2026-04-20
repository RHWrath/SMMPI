import os
from datetime import datetime


class Session:
    """Holds session state: officer name, active case, and paths."""

    def __init__(self, officer_name, case_number, case_root):
        self.officer_name = officer_name
        self.case_number = case_number
        self.case_root = case_root
        self.case_path = os.path.join(case_root, case_number)
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
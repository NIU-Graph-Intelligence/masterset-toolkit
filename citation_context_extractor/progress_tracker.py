"""Progress tracking for resume capability"""

import json
from pathlib import Path
from typing import Set, Dict, Any, List
from datetime import datetime


class ProgressTracker:
    """Track processed, skipped, and errored files for resume capability."""

    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.processed_files: Set[str] = set()
        self.skipped_files: Dict[str, str] = {}   # {file_path: reason}
        self.error_files: Dict[str, str] = {}      # {file_path: error_message}
        self.stats: Dict[str, Any] = {}
        self.load_progress()

    def load_progress(self):
        """Load progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get('processed_files', []))
                    self.skipped_files = data.get('skipped_files', {})
                    self.error_files = data.get('error_files', {})
                    self.stats = data.get('stats', {})
                total_done = len(self.processed_files) + len(self.skipped_files) + len(self.error_files)
                print(f"Loaded progress: {len(self.processed_files)} processed, "
                      f"{len(self.skipped_files)} skipped, "
                      f"{len(self.error_files)} errors")
            except Exception as e:
                print(f"Warning: Could not load progress file: {e}")
                print("Starting fresh...")

    def save_progress(self):
        """Save progress to file."""
        try:
            data = {
                'processed_files': sorted(list(self.processed_files)),
                'skipped_files': self.skipped_files,
                'error_files': self.error_files,
                'stats': self.stats,
                'last_updated': datetime.now().isoformat(),
            }

            self.progress_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")

    # ---------------------------------------------------------
    # Processed
    # ---------------------------------------------------------
    def is_processed(self, file_path: Path) -> bool:
        return str(file_path) in self.processed_files

    def mark_processed(self, file_path: Path):
        self.processed_files.add(str(file_path))

    def get_processed_count(self) -> int:
        return len(self.processed_files)

    # ---------------------------------------------------------
    # Skipped
    # ---------------------------------------------------------
    def is_skipped(self, file_path: Path) -> bool:
        return str(file_path) in self.skipped_files

    def mark_skipped(self, file_path: Path, reason: str):
        self.skipped_files[str(file_path)] = reason

    def get_skipped_count(self) -> int:
        return len(self.skipped_files)

    # ---------------------------------------------------------
    # Errors
    # ---------------------------------------------------------
    def is_error(self, file_path: Path) -> bool:
        return str(file_path) in self.error_files

    def mark_error(self, file_path: Path, error_message: str):
        self.error_files[str(file_path)] = error_message

    def get_error_count(self) -> int:
        return len(self.error_files)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def is_done(self, file_path: Path) -> bool:
        """Check if a file has been handled (processed, skipped, or errored)."""
        s = str(file_path)
        return s in self.processed_files or s in self.skipped_files or s in self.error_files

    def update_stats(self, key: str, value: Any):
        self.stats[key] = value

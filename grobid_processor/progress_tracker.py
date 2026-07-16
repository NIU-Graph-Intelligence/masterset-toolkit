"""Progress tracking for resume capability"""

import json
from pathlib import Path
from typing import Set, Dict, Any
from datetime import datetime

class ProgressTracker:
    """Track processed files for resume capability"""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.processed_files: Set[str] = set()
        self.error_files: Dict[str, str] = {}  # {file_path: error_message}
        self.stats: Dict[str, Any] = {}
        self.load_progress()
    
    def load_progress(self):
        """Load progress from file"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get('processed_files', []))
                    self.error_files = data.get('error_files', {})
                    self.stats = data.get('stats', {})
                print(f"Loaded progress: {len(self.processed_files)} files already processed")
                if self.error_files:
                    print(f"Found {len(self.error_files)} files with errors from previous runs")
            except Exception as e:
                print(f"Warning: Could not load progress file: {e}")
                print("Starting fresh...")
    
    def save_progress(self):
        """Save progress to file"""
        try:
            data = {
                'processed_files': sorted(list(self.processed_files)),
                'error_files': self.error_files,
                'stats': self.stats,
                'last_updated': datetime.now().isoformat()
            }
            
            # Ensure directory exists
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
    
    def is_processed(self, file_path: Path) -> bool:
        """Check if a file has been processed"""
        return str(file_path) in self.processed_files
    
    def mark_processed(self, file_path: Path):
        """Mark a file as processed"""
        self.processed_files.add(str(file_path))
    
    def mark_error(self, file_path: Path, error_message: str):
        """Mark a file as having an error"""
        # Store both the PDF path and output path for clarity
        self.error_files[str(file_path)] = error_message
    
    def is_error(self, file_path: Path) -> bool:
        """Check if a file has been marked as error"""
        return str(file_path) in self.error_files
    
    def get_error_count(self) -> int:
        """Get count of files with errors"""
        return len(self.error_files)
    
    def update_stats(self, key: str, value: Any):
        """Update statistics"""
        self.stats[key] = value
    
    def get_processed_count(self) -> int:
        """Get count of processed files"""
        return len(self.processed_files)
    
    def filter_unprocessed(self, file_list: list) -> list:
        """Filter out already processed files"""
        unprocessed = []
        for file_path in file_list:
            output_path = self._get_output_path(file_path)
            if not output_path.exists() and not self.is_processed(output_path):
                unprocessed.append(file_path)
        return unprocessed
    
    def _get_output_path(self, pdf_path: Path) -> Path:
        """Get expected output path for a PDF"""
        # This is a helper method that should match the logic in processor
        # We'll check if the output file exists
        return pdf_path
    
    def count_existing_outputs(self, output_paths: list) -> int:
        """Count how many output files already exist"""
        count = 0
        for output_path in output_paths:
            if Path(output_path).exists():
                count += 1
        return count
"""Core Prompt Generator Processor — traverses citation context JSONs and produces prompt text files."""

import json
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm

from .config import Config
from .progress_tracker import ProgressTracker
from .prompt_builder import (
    format_contexts,
    build_citation_info,
    build_type1_prompt,
    build_type2_prompt,
)


class PromptGeneratorProcessor:
    """Process citation context JSON files and generate prompt text files with resume capability."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.progress_tracker: Optional[ProgressTracker] = None

    # ---------------------------------------------------------
    # Progress tracker initialisation
    # ---------------------------------------------------------
    def _initialize_progress_tracker(self, conference: str, years: Optional[List[int]] = None):
        """Create a progress tracker unique to this conference/year combination."""
        if years:
            years_sorted = sorted(years)
            years_str = f"{years_sorted[0]}-{years_sorted[-1]}_n{len(years_sorted)}"
            filename = f"generate_prompts_progress_{conference}_{years_str}.json"
        else:
            filename = f"generate_prompts_progress_{conference}_all.json"

        self.progress_tracker = ProgressTracker(Path(filename))

    # ---------------------------------------------------------
    # File discovery
    # ---------------------------------------------------------
    def find_json_files(self, conference: str, years: Optional[List[int]] = None) -> List[Path]:
        """Find all .json files for a conference and optional years."""
        json_paths: List[Path] = []

        if years:
            for year in years:
                input_dir = self.config.get_input_dir(conference, year)
                if input_dir.exists():
                    jsons = sorted(input_dir.glob("*.json"))
                    json_paths.extend(jsons)
                    print(f"  Found {len(jsons)} JSON files in {conference}/{year}")
                else:
                    print(f"  Warning: Directory not found: {input_dir}")
        else:
            conf_dir = self.config.get_input_dir(conference)
            if conf_dir.exists():
                year_dirs = sorted(
                    [d for d in conf_dir.iterdir() if d.is_dir() and d.name.isdigit()]
                )
                for year_dir in year_dirs:
                    jsons = sorted(year_dir.glob("*.json"))
                    json_paths.extend(jsons)
                    print(f"  Found {len(jsons)} JSON files in {conference}/{year_dir.name}")
            else:
                print(f"  Warning: Conference directory not found: {conf_dir}")

        return json_paths

    # ---------------------------------------------------------
    # Derive paper title from JSON filename
    # ---------------------------------------------------------
    @staticmethod
    def get_paper_title(json_path: Path) -> str:
        """
        Extract human-readable paper title from JSON filename.
        Filename format: <id>_<Title_Words>.json
        e.g. o4CLLlIaaH_Learning_Robust_...json → Learning Robust ...
        """
        stem = json_path.stem
        parts = stem.split("_", 1)
        if len(parts) == 2:
            return parts[1].replace("_", " ")
        return stem.replace("_", " ")

    # ---------------------------------------------------------
    # Get output directory name (same as JSON stem)
    # ---------------------------------------------------------
    @staticmethod
    def get_paper_dir_name(json_path: Path) -> str:
        """Use the JSON filename (without extension) as the output folder name."""
        return json_path.stem

    # ---------------------------------------------------------
    # Get output directory path for a JSON file
    # ---------------------------------------------------------
    def get_output_dir(self, json_path: Path) -> Path:
        """Derive the output directory path from the input JSON path."""
        try:
            relative = json_path.parent.relative_to(self.config.INPUT_BASE)
        except ValueError:
            relative = Path("")
        return self.config.OUTPUT_BASE / relative / self.get_paper_dir_name(json_path)

    # ---------------------------------------------------------
    # Process a single JSON file
    # ---------------------------------------------------------
    def process_file(self, json_path: Path, output_dir: Path) -> dict:
        """
        Process one JSON file and generate prompt text files for each reference.

        Returns:
            dict with keys: 'total_refs', 'generated', 'empty'
        """
        with open(json_path, "r", encoding="utf-8") as f:
            references = json.load(f)

        paper_title = self.get_paper_title(json_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        stats = {"total_refs": len(references), "generated": 0, "empty": 0}

        for ref in references:
            target = ref["target"]
            citation_info = build_citation_info(ref)
            contexts = ref.get("contexts", [])
            formatted = format_contexts(contexts)
            in_dataset = ref["in_dataset"]
            in_conference_list = ref["in_conference_list"]

            if in_dataset == True or in_conference_list == True:
                is_empty = len(contexts) == 0
                type1_text = build_type1_prompt(paper_title, citation_info, formatted)
                type2_text = build_type2_prompt(paper_title, citation_info, formatted)

                if is_empty:
                    t1_name = f"ref_{target}_type_1_empty.txt"
                    t2_name = f"ref_{target}_type_2_empty.txt"
                    stats["empty"] += 1
                else:
                    t1_name = f"ref_{target}_type_1.txt"
                    t2_name = f"ref_{target}_type_2.txt"
                    stats["generated"] += 1

                (output_dir / t1_name).write_text(type1_text, encoding="utf-8")
                (output_dir / t2_name).write_text(type2_text, encoding="utf-8")

            else:
                # skipping the not found papers in the dataframe
                continue  

        return stats

    # ---------------------------------------------------------
    # Process a single conference
    # ---------------------------------------------------------
    def process_conference(self, conference: str, years: Optional[List[int]] = None):
        """Process all JSON files for a conference (and optional years)."""

        if not self.config.validate_conference(conference):
            print(f"Error: '{conference}' is not a supported conference.")
            print(f"Supported: {', '.join(self.config.CONFERENCES)}")
            return

        self._initialize_progress_tracker(conference, years)

        print(f"\n{'=' * 60}")
        print(f"Prompt Generation — {conference.upper()}")
        if years:
            print(f"Years: {', '.join(map(str, years))}")
        else:
            print("Years: ALL")
        print(f"{'=' * 60}\n")

        json_paths = self.find_json_files(conference, years)

        if not json_paths:
            print("No JSON files found to process.")
            return

        # ----- Partition into already-done vs to-do -----
        total_files = len(json_paths)
        already_done = 0
        files_to_process: List[tuple] = []

        for json_path in json_paths:
            output_dir = self.get_output_dir(json_path)

            if self.progress_tracker.is_done(output_dir):
                already_done += 1
            elif output_dir.exists() and any(output_dir.iterdir()):
                # Output dir exists with files but not tracked — mark as done
                already_done += 1
                self.progress_tracker.mark_processed(output_dir)
            else:
                files_to_process.append((json_path, output_dir))

        self.progress_tracker.save_progress()

        print(f"\n{'=' * 60}")
        print(f"Total JSON files found : {total_files}")
        print(f"Already done           : {already_done}")
        print(f"To process             : {len(files_to_process)}")
        print(f"{'=' * 60}\n")

        if not files_to_process:
            print("All files already processed!")
            return

        # ----- Process with progress bar -----
        processed_count = already_done
        error_count = self.progress_tracker.get_error_count()
        total_refs = 0
        total_empty = 0

        pbar = tqdm(total=total_files, initial=already_done, desc="Generating prompts")

        for json_path, output_dir in files_to_process:
            try:
                stats = self.process_file(json_path, output_dir)
                total_refs += stats["total_refs"]
                total_empty += stats["empty"]
                processed_count += 1
                self.progress_tracker.mark_processed(output_dir)

            except Exception as e:
                error_count += 1
                self.progress_tracker.mark_error(output_dir, str(e))
                tqdm.write(f"ERROR {json_path.name}: {e}")

            pbar.update(1)
            self.progress_tracker.save_progress()

        pbar.close()

        # ----- Final summary -----
        print(f"\n{'=' * 60}")
        print("Prompt generation complete!")
        print(f"{'=' * 60}")
        print(f"  Total JSON files  : {total_files}")
        print(f"  Processed         : {processed_count}")
        print(f"  Errors            : {error_count}")
        print(f"  Total references  : {total_refs}")
        print(f"  Empty contexts    : {total_empty}")
        if error_count > 0:
            print(f"\n  Error files are listed in: {self.progress_tracker.progress_file}")
            print(f"  Check the 'error_files' section for details.")
        print(f"  Output directory  : {self.config.OUTPUT_BASE / conference}")
        print(f"{'=' * 60}\n")

        self.progress_tracker.update_stats("total_processed", processed_count)
        self.progress_tracker.update_stats("total_errors", error_count)
        self.progress_tracker.save_progress()

    # ---------------------------------------------------------
    # Process ALL conferences
    # ---------------------------------------------------------
    def process_all(self):
        """Process every conference, every year."""
        for conference in self.config.CONFERENCES:
            self.process_conference(conference)

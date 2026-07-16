"""Core Citation Context Processor — traverses source files and produces .json outputs."""

import json
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm

from .config import Config
from .progress_tracker import ProgressTracker
from .extractor import (
    extract_citation_contexts,
    extract_citation_contexts_grobid,
    is_alpha_tag_mismatch,
)


class CitationContextProcessor:
    """Process nougat .md or GROBID .tei.xml files and extract citation contexts."""

    def __init__(self, config: Optional[Config] = None, source: str = "nougat"):
        self.config = config or Config()
        self.source = source
        self.progress_tracker: Optional[ProgressTracker] = None

    # ---------------------------------------------------------
    # Progress tracker initialisation
    # ---------------------------------------------------------
    def _initialize_progress_tracker(self, conference: str, years: Optional[List[int]] = None):
        """Create a progress tracker unique to this conference/year combination."""
        prefix = "grobid" if self.source == "grobid" else "citation_context"
        if years:
            years_str = "_".join(map(str, sorted(years)))
            filename = f"{prefix}_progress_{conference}_{years_str}.json"
        else:
            filename = f"{prefix}_progress_{conference}_all.json"

        self.progress_tracker = ProgressTracker(Path(filename))

    # ---------------------------------------------------------
    # File discovery — NOUGAT
    # ---------------------------------------------------------
    def find_md_files(self, conference: str, years: Optional[List[int]] = None) -> List[Path]:
        """Find all .md nougat files for a conference and optional years."""
        md_paths: List[Path] = []

        if years:
            for year in years:
                input_dir = self.config.get_input_dir(self.source, conference, year)
                if input_dir.exists():
                    mds = sorted(input_dir.glob("*.md"))
                    md_paths.extend(mds)
                    print(f"  Found {len(mds)} files in {conference}/{year}")
                else:
                    print(f"  Warning: Directory not found: {input_dir}")
        else:
            conf_dir = self.config.get_input_dir(self.source, conference)
            if conf_dir.exists():
                year_dirs = sorted(
                    [d for d in conf_dir.iterdir() if d.is_dir() and d.name.isdigit()]
                )
                for year_dir in year_dirs:
                    mds = sorted(year_dir.glob("*.md"))
                    md_paths.extend(mds)
                    print(f"  Found {len(mds)} files in {conference}/{year_dir.name}")
            else:
                print(f"  Warning: Conference directory not found: {conf_dir}")

        return md_paths

    # ---------------------------------------------------------
    # File discovery — GROBID
    # ---------------------------------------------------------
    def find_grobid_files(self, conference: str, years: Optional[List[int]] = None) -> List[Path]:
        """Find all .grobid.tei.xml files for a conference and optional years."""
        xml_paths: List[Path] = []

        if years:
            for year in years:
                input_dir = self.config.get_input_dir(self.source, conference, year)
                if input_dir.exists():
                    xmls = sorted(input_dir.glob("*.grobid.tei.xml"))
                    xml_paths.extend(xmls)
                    print(f"  Found {len(xmls)} GROBID files in {conference}/{year}")
                else:
                    print(f"  Warning: Directory not found: {input_dir}")
        else:
            conf_dir = self.config.get_input_dir(self.source, conference)
            if conf_dir.exists():
                year_dirs = sorted(
                    [d for d in conf_dir.iterdir() if d.is_dir() and d.name.isdigit()]
                )
                for year_dir in year_dirs:
                    xmls = sorted(year_dir.glob("*.grobid.tei.xml"))
                    xml_paths.extend(xmls)
                    print(f"  Found {len(xmls)} GROBID files in {conference}/{year_dir.name}")
            else:
                print(f"  Warning: Conference directory not found: {conf_dir}")

        return xml_paths

    # ---------------------------------------------------------
    # Path mapping: input ➜ output .json
    # ---------------------------------------------------------
    def get_output_path(self, input_path: Path) -> Path:
        """Derive the output .json path from the input file path.

        For nougat: paper.md → paper.json
        For grobid: paper.grobid.tei.xml → paper.json
        The relative conference/year structure is preserved.
        """
        if self.source == "grobid":
            input_base = self.config.GROBID_INPUT_BASE
            try:
                relative = input_path.relative_to(input_base)
            except ValueError:
                relative = Path(*input_path.parts[-3:])

            # Strip .grobid.tei.xml → .json
            # e.g. "paper_name.grobid.tei.xml" → "paper_name.json"
            stem = relative.name
            if stem.endswith(".grobid.tei.xml"):
                stem = stem[: -len(".grobid.tei.xml")]
            json_name = stem + ".json"
            return self.config.OUTPUT_BASE / relative.parent / json_name
        else:
            # Nougat: .md → .json
            input_base = self.config.NOUGAT_INPUT_BASE
            try:
                relative = input_path.relative_to(input_base)
            except ValueError:
                relative = Path(*input_path.parts[-3:])
            return self.config.OUTPUT_BASE / relative.with_suffix(".json")

    # ---------------------------------------------------------
    # Process a single NOUGAT file
    # ---------------------------------------------------------
    def process_file(self, md_path: Path, output_path: Path) -> str:
        """Process one .md file.

        Returns:
            'processed' — contexts extracted and saved
            'skipped'   — alpha-tag mismatch, file skipped
            'error'     — an exception occurred
        """
        # 1. Quick mismatch check (cheaper than full extraction)
        if is_alpha_tag_mismatch(str(md_path)):
            return "skipped"

        # 2. Full extraction
        results = extract_citation_contexts(str(md_path))

        # Double-check: extract_citation_contexts returns [] for mismatches too
        # (belt-and-suspenders)
        if results == [] and is_alpha_tag_mismatch(str(md_path)):
            return "skipped"

        # 3. Write JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return "processed"

    # ---------------------------------------------------------
    # Process a single GROBID file
    # ---------------------------------------------------------
    def process_grobid_file(self, xml_path: Path, output_path: Path) -> str:
        """Process one GROBID .tei.xml file.

        Returns:
            'processed' — contexts extracted and saved
            'error'     — an exception occurred

        Note: No alpha-tag mismatch check — that is a Nougat-only artefact.
        """
        results = extract_citation_contexts_grobid(str(xml_path))

        # Write JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return "processed"

    # ---------------------------------------------------------
    # Process a single conference — NOUGAT
    # ---------------------------------------------------------
    def _process_conference_nougat(self, conference: str, years: Optional[List[int]] = None):
        """Process all nougat files for a conference (and optional years)."""

        md_paths = self.find_md_files(conference, years)

        if not md_paths:
            print("No .md files found to process.")
            return

        # ----- Partition into already-done vs to-do -----
        total_files = len(md_paths)
        already_done = 0
        files_to_process: List[tuple] = []

        for md_path in md_paths:
            output_path = self.get_output_path(md_path)

            if output_path.exists():
                already_done += 1
                if not self.progress_tracker.is_done(output_path):
                    self.progress_tracker.mark_processed(output_path)
            elif self.progress_tracker.is_done(output_path):
                # Previously skipped or errored — count as done
                already_done += 1
            else:
                files_to_process.append((md_path, output_path))

        self.progress_tracker.save_progress()

        print(f"\n{'=' * 60}")
        print(f"Total .md files found : {total_files}")
        print(f"Already done           : {already_done}")
        print(f"To process             : {len(files_to_process)}")
        print(f"{'=' * 60}\n")

        if not files_to_process:
            print("All files already processed!")
            return

        # ----- Process with progress bar -----
        processed_count = already_done
        skipped_count = self.progress_tracker.get_skipped_count()
        error_count = self.progress_tracker.get_error_count()

        pbar = tqdm(total=total_files, initial=already_done, desc="Extracting contexts")

        for md_path, output_path in files_to_process:
            try:
                status = self.process_file(md_path, output_path)

                if status == "processed":
                    processed_count += 1
                    self.progress_tracker.mark_processed(output_path)
                elif status == "skipped":
                    skipped_count += 1
                    self.progress_tracker.mark_skipped(
                        output_path,
                        "Alpha-tag / numeric citation mismatch (Nougat conversion issue)",
                    )
                    tqdm.write(f"SKIP  {md_path.name}  (alpha-tag mismatch)")
                else:
                    error_count += 1
                    self.progress_tracker.mark_error(output_path, "Unknown status")

            except Exception as e:
                error_count += 1
                self.progress_tracker.mark_error(output_path, str(e))
                tqdm.write(f"ERROR {md_path.name}: {e}")

            pbar.update(1)
            # Save periodically (every file — cheap I/O for safety)
            self.progress_tracker.save_progress()

        pbar.close()

        # ----- Final summary -----
        print(f"\n{'=' * 60}")
        print("Processing complete!")
        print(f"{'=' * 60}")
        print(f"  Total files   : {total_files}")
        print(f"  Processed     : {processed_count}")
        print(f"  Skipped       : {skipped_count}")
        print(f"  Errors        : {error_count}")
        if skipped_count > 0:
            print(f"\n  Skipped files are listed in: {self.progress_tracker.progress_file}")
            print(f"  Check the 'skipped_files' section for details.")
        if error_count > 0:
            print(f"\n  Error files are listed in: {self.progress_tracker.progress_file}")
            print(f"  Check the 'error_files' section for details.")
        print(f"  Output directory: {self.config.OUTPUT_BASE / conference}")
        print(f"{'=' * 60}\n")

        self.progress_tracker.update_stats("total_processed", processed_count)
        self.progress_tracker.update_stats("total_skipped", skipped_count)
        self.progress_tracker.update_stats("total_errors", error_count)
        self.progress_tracker.save_progress()

    # ---------------------------------------------------------
    # Process a single conference — GROBID
    # ---------------------------------------------------------
    def _process_conference_grobid(self, conference: str, years: Optional[List[int]] = None):
        """Process GROBID files for a conference — only for papers missing JSON output.

        Traverses .grobid.tei.xml files and generates .json output ONLY for
        files that do not already have a corresponding .json (i.e., those that
        were NOT successfully processed by the Nougat pipeline).
        """

        xml_paths = self.find_grobid_files(conference, years)

        if not xml_paths:
            print("No .grobid.tei.xml files found to process.")
            return

        # ----- Determine which files already have JSON output -----
        total_grobid_files = len(xml_paths)
        already_have_json = 0
        files_to_process: List[tuple] = []

        for xml_path in xml_paths:
            output_path = self.get_output_path(xml_path)

            if output_path.exists():
                # JSON already produced (likely by Nougat) — skip
                already_have_json += 1
            elif self.progress_tracker.is_done(output_path):
                # Previously processed / errored by grobid run — skip
                already_have_json += 1
            else:
                files_to_process.append((xml_path, output_path))

        self.progress_tracker.save_progress()

        print(f"\n{'=' * 60}")
        print(f"Total GROBID XML files   : {total_grobid_files}")
        print(f"Already have JSON output : {already_have_json}")
        print(f"Missing — to process     : {len(files_to_process)}")
        print(f"{'=' * 60}\n")

        if not files_to_process:
            print("All files already have JSON output — nothing to do!")
            return

        # ----- Process with progress bar -----
        processed_count = 0
        error_count = self.progress_tracker.get_error_count()

        pbar = tqdm(total=len(files_to_process), desc="Extracting contexts (GROBID)")

        for xml_path, output_path in files_to_process:
            try:
                status = self.process_grobid_file(xml_path, output_path)

                if status == "processed":
                    processed_count += 1
                    self.progress_tracker.mark_processed(output_path)

            except Exception as e:
                error_count += 1
                self.progress_tracker.mark_error(output_path, str(e))
                tqdm.write(f"ERROR {xml_path.name}: {e}")

            pbar.update(1)
            self.progress_tracker.save_progress()

        pbar.close()

        # ----- Final summary -----
        print(f"\n{'=' * 60}")
        print("GROBID processing complete!")
        print(f"{'=' * 60}")
        print(f"  Total GROBID files       : {total_grobid_files}")
        print(f"  Already had JSON         : {already_have_json}")
        print(f"  Newly processed (GROBID) : {processed_count}")
        print(f"  Errors                   : {error_count}")
        if error_count > 0:
            print(f"\n  Error files are listed in: {self.progress_tracker.progress_file}")
            print(f"  Check the 'error_files' section for details.")
        print(f"  Output directory: {self.config.OUTPUT_BASE / conference}")
        print(f"{'=' * 60}\n")

        self.progress_tracker.update_stats("total_grobid_files", total_grobid_files)
        self.progress_tracker.update_stats("already_had_json", already_have_json)
        self.progress_tracker.update_stats("total_processed", processed_count)
        self.progress_tracker.update_stats("total_errors", error_count)
        self.progress_tracker.save_progress()

    # ---------------------------------------------------------
    # Process a single conference (dispatch)
    # ---------------------------------------------------------
    def process_conference(self, conference: str, years: Optional[List[int]] = None):
        """Process files for a conference (and optional years)."""

        if not self.config.validate_conference(conference):
            print(f"Error: '{conference}' is not a supported conference.")
            print(f"Supported: {', '.join(self.config.CONFERENCES)}")
            return

        self._initialize_progress_tracker(conference, years)

        print(f"\n{'=' * 60}")
        print(f"Citation Context Extraction — {conference.upper()}")
        print(f"Source: {self.source}")
        if years:
            print(f"Years: {', '.join(map(str, years))}")
        else:
            print("Years: ALL")
        print(f"{'=' * 60}\n")

        if self.source == "grobid":
            self._process_conference_grobid(conference, years)
        else:
            self._process_conference_nougat(conference, years)

    # ---------------------------------------------------------
    # Process ALL conferences
    # ---------------------------------------------------------
    def process_all(self):
        """Process every conference, every year."""
        for conference in self.config.CONFERENCES:
            self.process_conference(conference)


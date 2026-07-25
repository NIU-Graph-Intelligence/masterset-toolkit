"""Core GROBID TEI XML processor"""

from pathlib import Path
from typing import List, Optional
from grobid_client.grobid_client import GrobidClient, ServerUnavailableException
from tqdm import tqdm

from .config import Config
from .progress_tracker import ProgressTracker


class GrobidProcessor:
    """GROBID TEI XML processor with resume capability"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.client = None
        self.progress_tracker = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize GROBID client"""
        print(f"Connecting to GROBID server ({self.config.GROBID_SERVER})...")
        try:
            self.client = GrobidClient(
                grobid_server=self.config.GROBID_SERVER,
                batch_size=self.config.GROBID_BATCH_SIZE,
                sleep_time=self.config.GROBID_SLEEP_TIME,
                timeout=self.config.GROBID_TIMEOUT,
                coordinates=self.config.GROBID_COORDINATES,
                check_server=True,
            )
            print("Successfully connected to GROBID server")
        except ServerUnavailableException:
            raise ConnectionError(
                f"Could not connect to GROBID server at {self.config.GROBID_SERVER}. "
                "Make sure the GROBID server is running."
            )

    def _initialize_progress_tracker(
        self, conference: str, years: Optional[List[int]] = None
    ):
        """Initialize progress tracker with unique file per conference/year combo"""
        if years:
            years_sorted = sorted(years)
            years_str = f"{years_sorted[0]}-{years_sorted[-1]}_n{len(years_sorted)}"
            progress_filename = f"grobid_progress_{conference}_{years_str}.json"
        else:
            progress_filename = f"grobid_progress_{conference}_all.json"

        progress_file = Path(progress_filename)
        self.progress_tracker = ProgressTracker(progress_file)

    def find_pdfs(
        self, conference: str, years: Optional[List[int]] = None
    ) -> List[Path]:
        """Find all PDFs for a conference and optional years"""
        pdf_paths = []

        if years:
            # Process specific years
            for year in years:
                pdf_dir = self.config.get_pdf_dir(conference, year)
                if pdf_dir.exists():
                    pdfs = list(pdf_dir.glob("*.pdf"))
                    pdf_paths.extend(pdfs)
                    print(f"Found {len(pdfs)} PDFs in {conference}/{year}")
                else:
                    print(f"Warning: Directory not found: {pdf_dir}")
        else:
            # Process all years
            conf_dir = self.config.get_pdf_dir(conference)
            if conf_dir.exists():
                # Find all year subdirectories
                year_dirs = [
                    d for d in conf_dir.iterdir() if d.is_dir() and d.name.isdigit()
                ]
                for year_dir in sorted(year_dirs):
                    pdfs = list(year_dir.glob("*.pdf"))
                    pdf_paths.extend(pdfs)
                    print(f"Found {len(pdfs)} PDFs in {conference}/{year_dir.name}")
            else:
                print(f"Warning: Conference directory not found: {conf_dir}")

        return pdf_paths

    def get_output_path(self, pdf_path: Path) -> Path:
        """Generate output path based on PDF path.

        For a PDF like: .../papers/icml/2023/some_paper.pdf
        Output will be: .../grobid_output/icml/2023/some_paper.grobid.tei.xml
        """
        try:
            relative_path = pdf_path.relative_to(self.config.PDF_BASE_DIR)
        except ValueError:
            # Handle absolute paths elsewhere
            relative_path = Path(*pdf_path.parts[-3:])

        # Replace .pdf with .grobid.tei.xml
        output_path = self.config.GROBID_OUTPUT_BASE / relative_path.parent / (
            relative_path.stem + self.config.OUTPUT_EXTENSION
        )
        return output_path

    def process_pdf_with_grobid(self, pdf_path: Path) -> Optional[str]:
        """Process a single PDF file with GROBID and return the TEI XML string"""
        try:
            pdf_file, status, result_text = self.client.process_pdf(
                service="processFulltextDocument",
                pdf_file=str(pdf_path),
                generateIDs=self.config.GENERATE_IDS,
                consolidate_header=self.config.CONSOLIDATE_HEADER,
                consolidate_citations=self.config.CONSOLIDATE_CITATIONS,
                include_raw_citations=self.config.INCLUDE_RAW_CITATIONS,
                include_raw_affiliations=self.config.INCLUDE_RAW_AFFILIATIONS,
                tei_coordinates=self.config.TEI_COORDINATES,
                segment_sentences=self.config.SEGMENT_SENTENCES,
            )

            if status == 200:
                return result_text
            else:
                raise RuntimeError(
                    f"GROBID returned status {status}: {result_text[:200] if result_text else 'No response'}"
                )

        except Exception as e:
            raise RuntimeError(f"GROBID processing failed: {e}")

    def process_conference(self, conference: str, years: Optional[List[int]] = None):
        """Process all PDFs for a conference"""

        # Validate conference
        if not self.config.validate_conference(conference):
            print(f"Error: '{conference}' is not a supported conference")
            print(f"Supported conferences: {', '.join(self.config.CONFERENCES)}")
            return

        # Initialize progress tracker
        self._initialize_progress_tracker(conference, years)

        # Find all PDFs
        print(f"\n{'='*60}")
        print(f"Processing conference: {conference.upper()}")
        if years:
            print(f"Years: {', '.join(map(str, years))}")
        else:
            print("Years: ALL")
        print(f"{'='*60}\n")

        pdf_paths = self.find_pdfs(conference, years)

        if not pdf_paths:
            print("No PDFs found to process.")
            return

        # Check which files are already processed and update progress tracker
        total_files = len(pdf_paths)
        already_processed = 0
        files_to_process = []
        output_paths = []

        for pdf_path in pdf_paths:
            output_path = self.get_output_path(pdf_path)
            output_paths.append(output_path)

            if output_path.exists():
                already_processed += 1
                # Mark as processed in tracker if not already marked
                if not self.progress_tracker.is_processed(output_path):
                    self.progress_tracker.mark_processed(output_path)
            else:
                files_to_process.append((pdf_path, output_path))

        # Save progress after loading existing files
        self.progress_tracker.save_progress()

        print(f"\n{'='*60}")
        print(f"Total PDFs found: {total_files}")
        print(f"Already processed: {already_processed}")
        print(f"To process: {len(files_to_process)}")
        print(f"{'='*60}\n")

        if not files_to_process:
            print("All files already processed!")
            return

        # Process files with progress bar starting from already processed count
        processed_count = already_processed
        error_count = 0

        # Create progress bar with initial value
        pbar = tqdm(total=total_files, initial=already_processed, desc="Processing PDFs")

        for pdf_path, output_path in files_to_process:
            try:
                # Create output directory
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Process PDF with GROBID
                tei_xml = self.process_pdf_with_grobid(pdf_path)

                if tei_xml:
                    # Save TEI XML file
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(tei_xml)

                    processed_count += 1
                    self.progress_tracker.mark_processed(output_path)
                    self.progress_tracker.save_progress()
                else:
                    error_count += 1
                    error_msg = "No TEI XML returned from GROBID"
                    self.progress_tracker.mark_error(pdf_path, error_msg)
                    tqdm.write(f"Error: {error_msg} - {pdf_path.name}")

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                self.progress_tracker.mark_error(pdf_path, error_msg)
                tqdm.write(f"Error processing {pdf_path.name}: {error_msg}")

            pbar.update(1)

        pbar.close()

        # Final statistics
        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"{'='*60}")
        print(f"Total PDFs: {total_files}")
        print(f"Successfully processed: {processed_count}")
        print(f"Errors: {error_count}")
        if error_count > 0:
            print(
                f"\nFiles with errors are listed in: {self.progress_tracker.progress_file}"
            )
            print(f"Check the 'error_files' section for details.")
        print(f"Output directory: {self.config.GROBID_OUTPUT_BASE / conference}")
        print(f"{'='*60}\n")

        # Update final stats
        self.progress_tracker.update_stats("total_processed", processed_count)
        self.progress_tracker.update_stats("total_errors", error_count)
        self.progress_tracker.save_progress()

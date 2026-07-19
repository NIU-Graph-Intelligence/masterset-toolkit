# Nougat OCR Processor

A robust package for processing academic papers using Nougat OCR with resume capability and flexible command-line interface.

## Features

- ✅ **Resume Capability**: Automatically resumes processing from where it left off
- ✅ **Progress Tracking**: Keeps track of processed files to avoid reprocessing
- ✅ **Flexible CLI**: Process entire conferences or specific years
- ✅ **Multiple Year Support**: Process multiple years in a single command
- ✅ **Error Handling**: Gracefully handles errors and continues processing
- ✅ **Progress Visualization**: Shows real-time progress with tqdm

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the package structure is set up correctly (see structure below)

## Package Structure

```
.
├── nougat.py                           # Main entry point
├── requirements.txt                    # Python dependencies
├── README.md                           # Parent README
└── nougat_processor/                   # Package directory
    ├── __init__.py                     # Package initialization
    ├── config.py                       # Configuration settings
    ├── processor.py                    # Core Nougat processor
    ├── progress_tracker.py             # Progress tracking for resume
    └── cli.py                          # Command-line interface
    └── README_NOUGAT.md                # This file (README for Nougat package)
```

## Usage

### Basic Commands

Process all years of a conference:
```bash
python nougat.py icml
```

Process a specific year:
```bash
python nougat.py aistats 2025
```

Process multiple years:
```bash
python nougat.py emnlp 2022 2023 2024
```

Process GROBID fallback list (PDFs that GROBID failed on):
```bash
python nougat.py --fallback
```

### Supported Conferences

- aaai
- acl
- aistats
- colt
- cvpr
- eccv
- emnlp
- iccv
- iclr
- icml
- ijcai
- jmlr
- naacl
- neurips
- uai

### Help

```bash
python nougat.py --help
```

## How Resume Capability Works

1. **Progress Files**: For each conference/year combination, a JSON progress file is created (e.g., `nougat_progress_icml_2023.json`)

2. **Output Checking**: Before processing, the script checks if output `.md` files already exist

3. **Progress Bar**: The progress bar starts from the number of already-processed files

4. **Interruption Handling**: If interrupted (Ctrl+C), progress is saved and you can resume by running the same command again

5. **Automatic Resume**: When you restart, the script:
   - Counts existing output files
   - Skips already-processed PDFs
   - Updates the progress bar accordingly
   - Continues processing remaining files

## Configuration

Edit `nougat_processor/config.py` to change:
- Base directories for PDFs and outputs
- Model settings (model name, device)
- Nougat generation parameters
- DPI for PDF rendering

## Examples

### Example 1: Process entire CVPR conference
```bash
python nougat.py cvpr
```
This processes all PDFs in `../data/masterset/papers/cvpr/*/` (all years)

### Example 2: Process specific year
```bash
python nougat.py icml 2024
```
This processes only `../data/masterset/papers/icml/2024/`

### Example 3: Process multiple years
```bash
python nougat.py neurips 2020 2021 2022 2023 2024
```
This processes PDFs from all specified years

### Example 4: Resume after interruption
```bash
# Start processing
python nougat.py emnlp 2023
# Press Ctrl+C to interrupt
# Resume processing
python nougat.py emnlp 2023
# The script will skip already-processed files and continue
```

## Fallback Mode

The `--fallback` flag processes a predefined list of PDFs that GROBID failed to handle. These paths are hardcoded in `config.py` under `FALLBACK_PDFS`. Output goes to the standard `nougat_output/{conf}/{year}/` directories. Already-processed files are skipped automatically, so it's safe to re-run after interruption.

```bash
python nougat.py --fallback
```

To update the list, edit the `FALLBACK_PDFS` list in `nougat_processor/config.py`.

## Output

- Processed papers are saved as Markdown files (`.md`)
- Output directory structure mirrors the input PDF structure
- Each PDF `paper.pdf` becomes `paper.md` in the corresponding output directory

## Error Handling

- Missing directories are reported but don't stop processing
- PDF reading errors are logged and skipped
- Invalid years in command are warned and skipped
- Progress is saved regularly to enable resume

## Notes

- The script uses GPU if available (CUDA), otherwise falls back to CPU
- Progress files are saved in the current working directory
- Each conference/year combination has its own progress file for better tracking
- All existing output files are automatically detected and skipped

## Troubleshooting

**Issue**: "Conference directory not found"
- Check if the PDF base directory path is correct in `config.py`
- Verify the conference name is spelled correctly

**Issue**: "No PDFs found"
- Ensure PDFs exist in the expected directory structure
- Check that year directories exist under the conference directory

**Issue**: Processing is slow
- Nougat OCR is computationally intensive
- Ensure CUDA is available for GPU acceleration
- Consider processing smaller batches (specific years)
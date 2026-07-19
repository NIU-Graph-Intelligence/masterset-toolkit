# Generate Prompts

A package for generating prompt text files from citation context JSONs with resume capability and flexible command-line interface.

## Features

- ✅ **Resume Capability**: Automatically resumes processing from where it left off
- ✅ **Progress Tracking**: Keeps track of processed and errored files
- ✅ **Flexible CLI**: Process all conferences, a single conference, or specific years
- ✅ **Multiple Year Support**: Process multiple years in a single command
- ✅ **Prompt Type Generation**: Generates two prompt types (Type 1 and Type 2) with and without contexts
- ✅ **Output Organization**: Creates structured directory hierarchy matching input structure
- ✅ **Error Handling**: Gracefully handles errors and continues processing
- ✅ **Progress Visualization**: Shows real-time progress with tqdm

## Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

Or install specific dependencies:
```bash
pip install tqdm
```

## Package Structure

```
.
├── generate_prompts.py                # Convenience entry point
├── requirements.txt                   # Python dependencies
├── README_GENERATE_PROMPTS.md         # This file
└── generate_prompts/                  # Package directory
    ├── __init__.py                    # Package initialization
    ├── __main__.py                    # Enables: python -m generate_prompts
    ├── cli.py                         # Command-line interface & argument parsing
    ├── config.py                      # Configuration (directories, conferences)
    ├── processor.py                   # Core file discovery and processing logic
    ├── progress_tracker.py            # Progress tracking for resume capability
    └── prompt_builder.py              # Prompt text formatting and building
```

## Usage

### Basic Commands

**Process ALL conferences (all years):**
```bash
python generate_prompts.py
```

**Process all years of a specific conference:**
```bash
python generate_prompts.py icml
```

**Process a specific year:**
```bash
python generate_prompts.py icml 2024
```

**Process multiple years:**
```bash
python generate_prompts.py emnlp 2022 2023 2024
```

**Using the python -m syntax:**
```bash
python -m generate_prompts icml
python -m generate_prompts icml 2024 2025
```

### Help

```bash
python generate_prompts.py --help
```

or

```bash
python -m generate_prompts --help
```

### Supported Conferences

aaai, acl, aistats, colt, cvpr, eccv, emnlp, iccv, iclr, icml, ijcai, jmlr, naacl, neurips, uai

## How It Works

### Processing Pipeline

1. **Discover** all `.json` files under `<input_base>/<conference>/<year>/`
   - Input source: Citation context JSONs from the citation_context_extractor package

2. **Check resume** — skip files whose outputs already exist or are tracked in the progress file

3. **For each JSON file:**
   - **Load references** — read the citation context JSON file
   - **For each reference:**
     - **Extract citation info** — target reference, authors, year, venue, etc.
     - **Format contexts** — prepare citation context strings
     - **Generate prompts** — create Type 1 and Type 2 prompt files
     - **Handle empty contexts** — create separate `_empty.txt` files when contexts are missing
   - **Create output directory** — structure matches input directory hierarchy
   - **Write prompt files** — save `ref_<target>_type_<N>.txt` files

4. **Save progress** after each file

### Output Structure

For an input JSON at:
```
citation_contexts/icml/2024/paper_id_Paper_Title.json
```

The output will be structured as:
```
generated_prompts_filtered/icml/2024/paper_id_Paper_Title/
├── ref_b0_type_1.txt              # Type 1 prompt with contexts
├── ref_b0_type_2.txt              # Type 2 prompt with contexts
├── ref_b1_type_1.txt
├── ref_b1_type_2.txt
├── ref_b2_type_1_empty.txt        # Type 1 prompt without contexts
├── ref_b2_type_2_empty.txt        # Type 2 prompt without contexts
└── ...
```

### Prompt File Naming

- `ref_<target>_type_1.txt` — Type 1 prompt format with citation contexts (when contexts exist)
- `ref_<target>_type_2.txt` — Type 2 prompt format with citation contexts (when contexts exist)
- `ref_<target>_type_1_empty.txt` — Type 1 prompt format without contexts (when contexts are empty)
- `ref_<target>_type_2_empty.txt` — Type 2 prompt format without contexts (when contexts are empty)

Where `<target>` is the reference identifier (e.g., b0, b1, b2, etc.)

### Filtering Criteria

Only references matching the following criteria are processed:
- References marked as `in_dataset: True` or `in_conference_list: True` in the citation context JSON

This ensures that only relevant references are converted into prompts.

## How Resume Capability Works

1. **Progress Files**: For each conference/year combination, a JSON progress file is created (e.g., `generate_prompts_progress_icml_2024.json`)

2. **Output Checking**: Before processing, the script checks if output directories already exist

3. **Skip/Error Tracking**: Skipped and errored files are recorded in the progress JSON so they aren't re-attempted

4. **Progress Bar**: The progress bar starts from the number of already-done files

5. **Automatic Resume**: When you restart, the script:
   - Counts existing output directories
   - Recognizes previously skipped/errored files
   - Skips all of the above
   - Continues processing remaining files

## Configuration

Edit `generate_prompts/config.py` to change:
- Input base directory for citation context JSON files
- Output base directory for prompt text files
- Supported conferences list

Default paths:
- JSON input: `/home/ratul/masterset-recommendation/data/citation_contexts/<conference>/<year>/`
- Prompt output: `/home/ratul/masterset-recommendation/data/generated_prompts_filtered/<conference>/<year>/`

## Examples

### Example 1: Process everything
```bash
python generate_prompts.py
```
This processes all citation context JSONs from all conferences and all years, generating prompts.

### Example 2: Process entire CVPR conference
```bash
python generate_prompts.py cvpr
```
This processes all JSONs under `citation_contexts/cvpr/*/` (all years)

### Example 3: Process specific year
```bash
python generate_prompts.py icml 2024
```
This processes only `citation_contexts/icml/2024/`

### Example 4: Process multiple years
```bash
python generate_prompts.py neurips 2020 2021 2022 2023 2024
```
This processes JSONs from all specified years

### Example 5: Resume after interruption
```bash
# Start processing
python generate_prompts.py emnlp 2023
# Press Ctrl+C to interrupt
# Resume processing (same command)
python generate_prompts.py emnlp 2023
# The script will skip already-processed papers and continue
```

## Dependencies

- **tqdm** — progress bar visualization
- **citation_context_extractor** — upstream package providing input JSON files
- Python 3.7+

## Error Handling

- Invalid years in arguments are skipped with a warning
- Missing input directories are reported but don't stop processing
- File read/write errors are logged in the progress JSON
- The script continues processing other files even when errors occur

## Progress Tracking

Progress files are stored as JSON with the following structure:

```json
{
  "conference": "icml",
  "years": [2023, 2024],
  "processed": 250,
  "errored": 3,
  "error_details": {
    "paper_id_1.json": "Description of error",
    "paper_id_2.json": "Description of error"
  }
}
```

## Troubleshooting

### No output files generated

1. Check that input JSON files exist at the configured INPUT_BASE path
2. Verify that at least one reference in each JSON has `in_dataset: True` or `in_conference_list: True`
3. Run with `--help` to verify the correct paths are being used

### Resume not working

1. Delete or rename the progress JSON file (e.g., `generate_prompts_progress_icml_2024.json`)
2. Re-run the command to start fresh

### Memory issues with large years

If processing large years causes memory issues:
1. Process one year at a time instead of multiple years
2. Process one conference at a time instead of all conferences
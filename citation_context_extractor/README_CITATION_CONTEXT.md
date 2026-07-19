# Citation Context Extractor

A package for extracting citation contexts from Nougat OCR output files (`.md`) and GROBID TEI XML files (`.grobid.tei.xml`) with resume capability, skip detection, and flexible command-line interface.

## Features

- ✅ **Resume Capability**: Automatically resumes processing from where it left off
- ✅ **Progress Tracking**: Keeps track of processed, skipped, and errored files
- ✅ **Skip Detection**: Automatically skips files with alpha-tag / numeric citation mismatch (a known Nougat artefact)
- ✅ **Flexible CLI**: Process all conferences, a single conference, or specific years
- ✅ **Multiple Year Support**: Process multiple years in a single command
- ✅ **Source Flag**: `--nougat` for Nougat files, `--grobid` for GROBID TEI XML files
- ✅ **JSON Output**: One `.json` file per paper, mirroring the nougat directory structure
- ✅ **Error Handling**: Gracefully handles errors and continues processing
- ✅ **Progress Visualization**: Shows real-time progress with tqdm

## Package Structure

```
.
├── extract_contexts.py                     # Convenience entry point
├── README_CITATION_CONTEXT.md              # This file
└── citation_context_extractor/             # Package directory
    ├── __init__.py                         # Package initialization
    ├── __main__.py                         # Enables: python -m citation_context_extractor
    ├── cli.py                              # Command-line interface & argument parsing
    ├── config.py                           # Configuration (directories, conferences)
    ├── extractor.py                        # Wraps extract_titles.py & test-extract-contexts.py
    ├── processor.py                        # Core traversal, skip detection, JSON output
    └── progress_tracker.py                 # Progress tracking for resume (processed/skipped/errors)
```

### Dependencies on Existing Modules

The package imports the proven extraction logic from:

- `preprocessing/extract_titles.py` — reference title & year extraction
- `preprocessing/test-extract-contexts.py` — citation context extraction, alpha-tag mismatch detection
- `preprocessing/test-extract-contexts-grobid.py` — GROBID TEI XML citation context extraction

These files are loaded via `importlib` at runtime. **No code is copied** — any improvements to those files are automatically picked up.

## Usage

### Basic Commands

**Process ALL conferences (all years):**
```bash
python -m citation_context_extractor --grobid
python -m citation_context_extractor --nougat
```

**Process all years of a specific conference:**
```bash
python -m citation_context_extractor --nougat icml
python -m citation_context_extractor --grobid icml
```

**Process a specific year:**
```bash
python -m citation_context_extractor --nougat aaai 2024
python -m citation_context_extractor --grobid icml 2024
```

**Process multiple years:**
```bash
python -m citation_context_extractor --nougat emnlp 2022 2023 2024
```

**Using the convenience script:**
```bash
python extract_contexts.py --nougat icml 2024
```

### Source Flags

| Flag       | Description                                                       |
|------------|-------------------------------------------------------------------|
| `--grobid` | Process GROBID `.grobid.tei.xml` files (fills in missing JSONs)   |
| `--nougat` | Process Nougat OCR `.md` files                                    |

### Help

```bash
python -m citation_context_extractor --help
```

### Supported Conferences

aaai, acl, aistats, colt, cvpr, eccv, emnlp, iccv, iclr, icml, ijcai, jmlr, naacl, neurips, uai

## How It Works

### Processing Pipeline — Nougat

1. **Discover** all `.md` files under `<nougat_root>/<conference>/<year>/`
2. **Check resume** — skip files whose output `.json` already exists or are tracked in the progress file
3. **For each file:**
   - **Alpha-tag mismatch check** — if references use `[DKS17]`-style tags but the body has `[5]`-style numeric cites (a Nougat conversion artefact), the file is **skipped** entirely
   - **Extract references** — titles, years from the reference section
   - **Extract cite keys** — determine how each reference is cited in the body
   - **Extract contexts** — 3-sentence windows around each citation occurrence
   - **Write JSON** — save results to the output directory
4. **Save progress** after each file

### Processing Pipeline — GROBID

1. **Discover** all `.grobid.tei.xml` files under `<grobid_root>/<conference>/<year>/`
2. **Check existing output** — if a `.json` already exists for a paper (produced by Nougat or a previous GROBID run), **skip** it
3. **For each missing file:**
   - **Parse TEI XML** — extract bibliography and body text with citation markers
   - **Extract contexts** — 3-sentence windows around each citation occurrence
   - **Write JSON** — save results to the **same** output directory as Nougat
4. **Save progress** after each file

### Alpha-Tag Mismatch Detection

Some papers use author-initial citation tags in their references (e.g., `[DKS17]`, `[GDDM14]`, `[KPR+17]`). When Nougat converts these papers, it replaces the in-body citations with sequential numbers (`[5]`, `[6, 7]`), making it impossible to map references to their in-text occurrences. These files are automatically detected and skipped — no JSON is produced for them.

## How Resume Capability Works

1. **Progress Files**: For each conference/year combination, a JSON progress file is created (e.g., `citation_context_progress_icml_2024.json`)

2. **Output Checking**: Before processing, the script checks if output `.json` files already exist

3. **Skip/Error Tracking**: Skipped and errored files are recorded in the progress JSON so they aren't re-attempted

4. **Progress Bar**: The progress bar starts from the number of already-done files

5. **Automatic Resume**: When you restart, the script:
   - Counts existing output files
   - Recognises previously skipped/errored files
   - Skips all of the above
   - Continues processing remaining files

## Configuration

Edit `citation_context_extractor/config.py` to change:
- Input base directory for Nougat files
- Output base directory for JSON files
- Supported conferences list

Default paths:
- Nougat input: `../data/nougat_output/<conference>/<year>/`
- GROBID input: `../data/grobid_output/<conference>/<year>/`
- JSON output: `../data/citation_contexts/<conference>/<year>/`

## Output Format

Each output `.json` file contains a list of references with their extracted citation contexts:

```json
[
  {
    "target": "b0",
    "title": "Random forests",
    "year": 2001,
    "cite": "Breiman (2001)",
    "contexts": [
      {
        "section": "Introduction",
        "context": "Previous sentence. The method proposed by Breiman (2001) uses an ensemble of decision trees to improve prediction accuracy. Next sentence."
      },
      {
        "section": "Related Work",
        "context": "Previous sentence. Random forests Breiman (2001) have been widely adopted. Next sentence."
      }
    ]
  },
  {
    "target": "b1",
    "title": "Texture synthesis by non-parametric sampling",
    "year": 1999,
    "cite": "Efros and Leung (1999)",
    "contexts": []
  }
]
```

Each context is a **3-sentence window**: previous sentence + citation sentence + next sentence (adjusted at section boundaries).

## Progress JSON Format

```json
{
  "processed_files": [
    "../data/masterset/citation_contexts/icml/2024/paper1.json",
    "../data/masterset/citation_contexts/icml/2024/paper2.json"
  ],
  "skipped_files": {
    "..data/.../paper3.json": "Alpha-tag / numeric citation mismatch (Nougat conversion issue)"
  },
  "error_files": {
    "..data/.../paper4.json": "UnicodeDecodeError: ..."
  },
  "stats": {
    "total_processed": 150,
    "total_skipped": 3,
    "total_errors": 1
  },
  "last_updated": "2026-03-13T14:30:00.000000"
}
```

## Examples

### Example 1: Process everything
```bash
python -m citation_context_extractor --nougat
```
Processes ALL Nougat `.md` files from all 15 conferences and all years.

### Example 2: Process entire AAAI conference
```bash
python -m citation_context_extractor --nougat aaai
```
Processes all years under `nougat_output/aaai/*/`

### Example 3: Process specific year
```bash
python -m citation_context_extractor --nougat emnlp 2023
```
Processes only `nougat_output/emnlp/2023/`

### Example 4: Process multiple years
```bash
python -m citation_context_extractor --nougat neurips 2020 2021 2022 2023 2024
```

### Example 5: Process missing files with GROBID
```bash
python -m citation_context_extractor --grobid icml
```
Traverses GROBID `.grobid.tei.xml` files for ICML and generates `.json` only for papers that don't already have one (from Nougat).

### Example 6: GROBID — specific year
```bash
python -m citation_context_extractor --grobid aaai 2024
```

### Example 7: Resume after interruption
```bash
# Start processing
python -m citation_context_extractor --nougat cvpr 2024
# Press Ctrl+C to interrupt
# Resume later — the script picks up where it left off
python -m citation_context_extractor --nougat cvpr 2024
```

## Error Handling

- Missing directories are reported but don't stop processing
- File reading errors are logged with specific error messages
- Alpha-tag mismatch files are cleanly skipped (not counted as errors) — Nougat only
- Invalid years in the command are warned and ignored
- Progress is saved after every file to enable safe resume
- All errors and skips are tracked in the progress JSON

## Notes

- The package does **not** modify or copy any code from `extract_titles.py`, `test-extract-contexts.py`, or `test-extract-contexts-grobid.py` — it imports them at runtime
- Output `.json` filenames match the input filenames (just the extension changes: `.md` → `.json`, `.grobid.tei.xml` → `.json`)
- Progress files are saved in the current working directory
- Each conference/year combination has its own progress file
- Nougat and GROBID use separate progress files (prefixed `citation_context_progress_` and `grobid_progress_` respectively)
- When processing all conferences, each conference gets its own progress file
- Skipped files (Nougat) produce **no** output JSON — they are only recorded in the progress JSON
- GROBID mode only processes papers whose JSON is missing — it never overwrites existing Nougat output

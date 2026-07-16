# GROBID TEI XML Processor

Process academic paper PDFs using GROBID to produce TEI XML output files.

## Prerequisites

1. A running GROBID server (default: `http://localhost:8070`)
2. Python dependencies:
   ```bash
   pip install grobid_client_python tqdm
   ```

### Starting the GROBID server (Docker)

```bash
sudo docker run --rm --init --ulimit core=0 \
    -p 8070:8070 -p 8071:8071 \
    grobid/grobid:0.8.2
```

## Usage

```bash
python grobid.py <conference> [year1] [year2] ...
```

### Examples

```bash
nohup python grobid.py icml > icml_grobid.log 2>&1 &                    # Process all years
python grobid.py aistats 2025            # Process only 2025
python grobid.py emnlp 2022 2023 2024    # Process multiple years
```

## Configuration

Edit `grobid_processor/config.py` to set:

- `PDF_BASE_DIR` — root directory containing PDFs as `{conference}/{year}/*.pdf`
- `GROBID_OUTPUT_BASE` — root directory for output `.grobid.tei.xml` files
- `GROBID_SERVER` — URL of the GROBID server

## Output

For a PDF at:
```
papers/icml/2023/some_paper.pdf
```
The output will be:
```
grobid_output/icml/2023/some_paper.grobid.tei.xml
```

## Resume Support

The processor automatically skips PDFs whose output XML files already exist. Progress is also tracked in JSON files (`grobid_progress_*.json`) so you can safely interrupt and resume.

## Supported Conferences

aaai, acl, aistats, colt, cvpr, eccv, emnlp, iccv, iclr, icml, ijcai, jmlr, naacl, neurips, uai

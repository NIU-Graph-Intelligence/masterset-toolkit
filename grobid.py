#!/usr/bin/env python
"""
GROBID TEI XML Processor - Main Entry Point

Usage:
    python grobid.py <conference> [year1] [year2] ...

Examples:
    python grobid.py icml                    # Process all years
    python grobid.py aistats 2025            # Process only 2025
    python grobid.py emnlp 2022 2023 2024    # Process multiple years
"""

from grobid_processor.cli import main

if __name__ == "__main__":
    main()

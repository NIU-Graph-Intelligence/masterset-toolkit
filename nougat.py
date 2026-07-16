#!/usr/bin/env python
"""
Nougat OCR Processor - Main Entry Point

Usage:
    python nougat.py <conference> [year1] [year2] ...

Examples:
    python nougat.py icml                    # Process all years
    python nougat.py aistats 2025            # Process only 2025
    python nougat.py emnlp 2022 2023 2024    # Process multiple years
"""

from nougat_processor.cli import main

if __name__ == "__main__":
    main()

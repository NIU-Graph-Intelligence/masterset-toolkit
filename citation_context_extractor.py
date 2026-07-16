#!/usr/bin/env python3
"""
Convenience entry point for Citation Context Extractor.

Usage:
    python extract_contexts.py --nougat                         # all conferences
    python extract_contexts.py --nougat <conf>                  # all years
    python extract_contexts.py --nougat <conf> <y1> [y2] ...    # specific years

See: python extract_contexts.py --help
"""

from citation_context_extractor.cli import main

if __name__ == "__main__":
    main()

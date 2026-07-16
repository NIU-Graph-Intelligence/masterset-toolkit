"""Command-line interface for Citation Context Extractor"""

import sys
from typing import List, Optional
from .processor import CitationContextProcessor
from .config import Config


def parse_arguments(args: List[str]) -> tuple:
    """
    Parse command line arguments.

    Expected formats:
        extract_contexts.py --nougat                          # all conferences, all years
        extract_contexts.py --nougat aaai                     # one conference, all years
        extract_contexts.py --nougat aaai 2024                # one conference, one year
        extract_contexts.py --nougat emnlp 2022 2023 2024     # one conference, multiple years

    Returns:
        tuple: (source, conference_or_None, years_list_or_None)
    """
    if not args:
        return None, None, None

    # First arg must be --nougat or --grobid
    source = None
    rest = args

    if args[0] in ("--nougat", "-nougat"):
        source = "nougat"
        rest = args[1:]
    elif args[0] in ("--grobid", "-grobid"):
        source = "grobid"
        rest = args[1:]
    else:
        # Legacy: no source flag — assume nougat if it looks like a conference
        # But be safe: require the flag
        return None, None, None

    if not rest:
        # --nougat with no conference → process all
        return source, None, None

    conference = rest[0].lower()
    years: List[int] = []
    for arg in rest[1:]:
        try:
            years.append(int(arg))
        except ValueError:
            print(f"Warning: '{arg}' is not a valid year, skipping...")

    return source, conference, years if years else None


def print_usage():
    """Print usage information."""
    config = Config()
    print("=" * 60)
    print("Citation Context Extractor — Usage")
    print("=" * 60)
    print()
    print("Usage:")
    print("  python -m citation_context_extractor --nougat                         # all conferences")
    print("  python -m citation_context_extractor --nougat <conf>                  # all years")
    print("  python -m citation_context_extractor --nougat <conf> <y1> [y2] ...    # specific years")
    print()
    print("Source flags:")
    print("  --nougat    Process Nougat OCR .md files")
    print("  --grobid    Process GROBID TEI XML files (fills in missing JSONs)")
    print()
    print("Examples:")
    print("  python -m citation_context_extractor --nougat icml")
    print("  python -m citation_context_extractor --nougat aaai 2024")
    print("  python -m citation_context_extractor --nougat emnlp 2022 2023 2024")
    print()
    print("Supported conferences:")
    for i, conf in enumerate(config.CONFERENCES, 1):
        end = "\n" if i % 5 == 0 else ", "
        print(f"  {conf}", end=end)
    print()
    print()
    print("Features:")
    print("  • Resume capability — re-run the same command to continue")
    print("  • Skips files with alpha-tag / numeric mismatch (Nougat artefact)")
    print("  • Progress JSON tracks processed, skipped, and errored files")
    print("=" * 60)


def main():
    """Main entry point for CLI."""
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print_usage()
        return

    source, conference, years = parse_arguments(args)

    if source is None:
        print("Error: You must specify a source (--nougat or --grobid)")
        print_usage()
        sys.exit(1)


    try:
        processor = CitationContextProcessor(source=source)

        if conference:
            processor.process_conference(conference, years)
        else:
            processor.process_all()

    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        print("Progress has been saved. Re-run the same command to resume.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

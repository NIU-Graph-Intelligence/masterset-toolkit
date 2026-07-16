"""Command-line interface for Nougat processor"""

import sys
from typing import List, Optional
from .processor import NougatProcessor
from .config import Config


def parse_arguments(args: List[str]) -> tuple:
    """
    Parse command line arguments

    Expected formats:
    - nougat.py icml
    - nougat.py aistats 2025
    - nougat.py emnlp 2022 2023 2024

    Returns:
        tuple: (conference, years_list or None)
    """
    if len(args) < 1:
        return None, None

    conference = args[0].lower()

    if len(args) == 1:
        # Process all years
        return conference, None

    # Parse years
    years = []
    for arg in args[1:]:
        try:
            year = int(arg)
            years.append(year)
        except ValueError:
            print(f"Warning: '{arg}' is not a valid year, skipping...")

    return conference, years if years else None


def print_usage():
    """Print usage information"""
    config = Config()
    print("=" * 60)
    print("Nougat OCR Processor - Usage")
    print("=" * 60)
    print("\nUsage:")
    print("  python nougat.py <conference> [year1] [year2] ...")
    print("\nExamples:")
    print("  python nougat.py icml                    # Process all years")
    print("  python nougat.py aistats 2025            # Process only 2025")
    print("  python nougat.py emnlp 2022 2023 2024    # Process multiple years")
    print("\nSupported conferences:")
    for i, conf in enumerate(config.CONFERENCES, 1):
        print(f"  {conf}", end="")
        if i % 5 == 0:
            print()
        else:
            print(", ", end="")
    print("\n" + "=" * 60)


def main():
    """Main entry point for CLI"""
    args = sys.argv[1:]

    if not args or args[0] in ["-h", "--help", "help"]:
        print_usage()
        return

    conference, years = parse_arguments(args)

    if not conference:
        print("Error: No conference specified")
        print_usage()
        sys.exit(1)

    # Create processor and run
    try:
        processor = NougatProcessor()
        processor.process_conference(conference, years)
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        print(
            "Progress has been saved. You can resume by running the same command again."
        )
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

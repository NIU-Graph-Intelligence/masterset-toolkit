"""Command-line interface for Generate Prompts"""

import sys
from typing import List, Optional
from .processor import PromptGeneratorProcessor
from .config import Config


def parse_arguments(args: List[str]) -> tuple:
    """
    Parse command line arguments.

    Expected formats:
        generate_prompts.py                              # all conferences, all years
        generate_prompts.py icml                         # one conference, all years
        generate_prompts.py icml 2025                    # one conference, one year
        generate_prompts.py icml 2020 2021 2025          # one conference, multiple years

    Returns:
        tuple: (conference_or_None, years_list_or_None)
    """
    if not args:
        return None, None

    conference = args[0].lower()
    years: List[int] = []
    for arg in args[1:]:
        try:
            years.append(int(arg))
        except ValueError:
            print(f"Warning: '{arg}' is not a valid year, skipping...")

    return conference, years if years else None


def print_usage():
    """Print usage information."""
    config = Config()
    print("=" * 60)
    print("Generate Prompts — Usage")
    print("=" * 60)
    print()
    print("Usage:")
    print("  python -m generate_prompts                              # all conferences, all years")
    print("  python -m generate_prompts <conf>                       # one conference, all years")
    print("  python -m generate_prompts <conf> <y1> [y2] ...         # specific years")
    print()
    print("Examples:")
    print("  python -m generate_prompts icml")
    print("  python -m generate_prompts icml 2025")
    print("  python -m generate_prompts icml 2020 2021 2025")
    print()
    print("Supported conferences:")
    for i, conf in enumerate(config.CONFERENCES, 1):
        end = "\n" if i % 5 == 0 else ", "
        print(f"  {conf}", end=end)
    print()
    print()
    print("Input:  Citation context JSONs from")
    print(f"        {config.INPUT_BASE}")
    print("Output: Prompt text files to")
    print(f"        {config.OUTPUT_BASE}")
    print()
    print("For each JSON file, a directory is created (named after the JSON).")
    print("Inside, two .txt files per reference:")
    print("  ref_b0_type_1.txt / ref_b0_type_2.txt         (with contexts)")
    print("  ref_b0_type_1_empty.txt / ref_b0_type_2_empty.txt (empty contexts)")
    print()
    print("Features:")
    print("  • Resume capability — re-run the same command to continue")
    print("  • Progress JSON tracks processed and errored files")
    print("=" * 60)


def main():
    """Main entry point for CLI."""
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help", "help"):
        print_usage()
        return

    try:
        processor = PromptGeneratorProcessor()

        if not args:
            # No arguments → process all conferences
            processor.process_all()
        else:
            conference, years = parse_arguments(args)
            if conference:
                processor.process_conference(conference, years)
            else:
                print_usage()

    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

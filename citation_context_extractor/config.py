"""Configuration settings for Citation Context Extractor"""
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Configuration class for Citation Context Extractor"""

    #set your own root path in .env file and make sure to use a fallback path as well
    ROOT_DIR = Path(os.getenv("ROOT_DIR", "/home/ratul/mustcite/"))

    # =========================================================
    # Nougat source directories
    # =========================================================
    NOUGAT_INPUT_BASE = ROOT_DIR / "data/nougat_output"

    # =========================================================
    # GROBID source directories
    # =========================================================
    GROBID_INPUT_BASE = ROOT_DIR / "data/grobid_output"

    # =========================================================
    # Output directory for extracted citation contexts
    # =========================================================
    OUTPUT_BASE = ROOT_DIR / "data/citation_contexts"

    # =========================================================
    # Supported conferences (same 15 as nougat_processor)
    # =========================================================
    CONFERENCES = [
        "aaai",
        "acl",
        "aistats",
        "colt",
        "cvpr",
        "eccv",
        "emnlp",
        "iccv",
        "iclr",
        "icml",
        "ijcai",
        "jmlr",
        "naacl",
        "neurips",
        "uai",
    ]

    # =========================================================
    # Progress tracking filename pattern
    # =========================================================
    PROGRESS_FILE = "citation_context_progress.json"

    # =========================================================
    # Directory helpers
    # =========================================================
    @classmethod
    def get_input_dir(cls, source: str, conference: str, year=None):
        """Get input directory for a given source, conference, and optional year."""
        if source == "nougat":
            base = cls.NOUGAT_INPUT_BASE
        elif source == "grobid":
            base = cls.GROBID_INPUT_BASE
        else:
            raise ValueError(f"Unsupported source: {source}. Use 'nougat' or 'grobid'.")

        if year:
            return base / conference / str(year)
        return base / conference

    @classmethod
    def get_output_dir(cls, conference: str, year=None):
        """Get output directory for a conference and optional year."""
        if year:
            return cls.OUTPUT_BASE / conference / str(year)
        return cls.OUTPUT_BASE / conference

    @classmethod
    def validate_conference(cls, conference: str) -> bool:
        """Validate if conference is supported."""
        return conference.lower() in cls.CONFERENCES

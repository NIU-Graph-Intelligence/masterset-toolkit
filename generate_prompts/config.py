"""Configuration settings for Generate Prompts"""
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Configuration class for Generate Prompts"""

    #set your own root path in .env file and make sure to use a fallback path as well
    ROOT_DIR = Path(os.getenv("ROOT_DIR", "/home/ratul/mustcite/"))

    # =========================================================
    # Input directory — citation context JSONs
    # =========================================================
    INPUT_BASE = ROOT_DIR / "data/citation_contexts"

    # =========================================================
    # Output directory for generated prompt text files
    # =========================================================
    OUTPUT_BASE = ROOT_DIR / "data/generated_prompts"

    # =========================================================
    # Supported conferences (same 15 as citation_context_extractor)
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
    # Directory helpers
    # =========================================================
    @classmethod
    def get_input_dir(cls, conference: str, year=None):
        """Get input directory for a given conference and optional year."""
        if year:
            return cls.INPUT_BASE / conference / str(year)
        return cls.INPUT_BASE / conference

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

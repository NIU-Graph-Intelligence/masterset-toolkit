"""Configuration settings for Nougat processor"""

from pathlib import Path
import torch


class Config:
    """Configuration class for Nougat OCR processor"""

    METADATA_BASE_DIR = Path("../data/masterset/metadata/")
    PDF_BASE_DIR = Path("../data/masterset/papers/")
    NOUGAT_OUTPUT_BASE = Path("../data/masterset/nougat_output")

    # Model settings
    MODEL_NAME = "facebook/nougat-small"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # Nougat generation parameters
    MIN_LENGTH = 1
    MAX_NEW_TOKENS = 3500
    REPETITION_PENALTY = 1.2
    DPI = 96

    # Supported conferences
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

    # Progress tracking
    PROGRESS_FILE = "nougat_progress.json"

    # Fallback list: PDFs that GROBID failed to process (103 files)
    # These will be processed by Nougat and saved to nougat_output/{conf}/{year}/
    # Run with: python nougat.py --fallback
    # This is a manual process as in, you have to put the paths of the failed PDFs in this FALLBACK_PDFS list manually
    # Examples of one entry is shown as a comment inside FALLBACK_PDFS list:
    FALLBACK_PDFS = [
        # "cvpr/2015/Song_Joint_Multi-Feature_Spatial_2015_CVPR_paper_Joint Multi-Feature Spatial Context for Scene Reco.pdf",
        # "iclr/2023/UvmDCdSPDOW_Information-Theoretic Diffusion.pdf",
    ]

    @classmethod
    def get_pdf_dir(cls, conference, year=None):
        """Get PDF directory for a conference and optional year"""
        if year:
            return cls.PDF_BASE_DIR / conference / str(year)
        return cls.PDF_BASE_DIR / conference

    @classmethod
    def get_output_dir(cls, conference, year=None):
        """Get output directory for a conference and optional year"""
        if year:
            return cls.NOUGAT_OUTPUT_BASE / conference / str(year)
        return cls.NOUGAT_OUTPUT_BASE / conference

    @classmethod
    def validate_conference(cls, conference):
        """Validate if conference is supported"""
        return conference.lower() in cls.CONFERENCES

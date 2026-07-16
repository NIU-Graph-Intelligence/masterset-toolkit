"""Configuration settings for GROBID processor"""

from pathlib import Path


class Config:
    """Configuration class for GROBID TEI XML processor"""

    # Base directories - For METIS
    # METADATA_BASE_DIR = Path("/lstr/sahara/graphlab/ratul/data/metadata/")
    # PDF_BASE_DIR = Path("/lstr/sahara/graphlab/ratul/data/papers/")
    # GROBID_OUTPUT_BASE = Path("/home/ratul/masterset-data-preparation/output/grobid_output")

    # Base directories - For 10.158.56.231 Server
    # METADATA_BASE_DIR = Path("/mnt/data/data/metadata/")
    # PDF_BASE_DIR = Path("/mnt/data/data/papers/")
    # GROBID_OUTPUT_BASE = Path("/home/ratul/masterset-recommendation/data/grobid_output")

    # Base directories - For lancer
    METADATA_BASE_DIR = Path("/home/ratul/masterset-recommendation/data/metadata/")
    PDF_BASE_DIR = Path("/home/ratul/masterset-recommendation/data/papers/")
    GROBID_OUTPUT_BASE = Path("/home/ratul/masterset-recommendation/data/grobid_output")

    # GROBID server settings
    GROBID_SERVER = "http://localhost:8070"
    GROBID_TIMEOUT = 60
    GROBID_BATCH_SIZE = 1000
    GROBID_SLEEP_TIME = 5
    GROBID_COORDINATES = ["persName", "figure", "ref", "biblStruct", "formula", "s"]

    # GROBID processing parameters (matching professor's settings)
    GENERATE_IDS = False
    CONSOLIDATE_HEADER = False
    CONSOLIDATE_CITATIONS = False
    INCLUDE_RAW_CITATIONS = False
    INCLUDE_RAW_AFFILIATIONS = False
    TEI_COORDINATES = False
    SEGMENT_SENTENCES = False

    # Output file extension
    OUTPUT_EXTENSION = ".grobid.tei.xml"

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
    PROGRESS_FILE = "grobid_progress.json"

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
            return cls.GROBID_OUTPUT_BASE / conference / str(year)
        return cls.GROBID_OUTPUT_BASE / conference

    @classmethod
    def validate_conference(cls, conference):
        """Validate if conference is supported"""
        return conference.lower() in cls.CONFERENCES

"""
Citation Context Extractor Package
Extract citation contexts from Nougat OCR output files with resume capability.
"""

from .processor import CitationContextProcessor
from .config import Config

__version__ = "1.0.0"
__all__ = ["CitationContextProcessor", "Config"]

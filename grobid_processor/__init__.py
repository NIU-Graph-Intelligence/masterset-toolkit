"""
GROBID TEI XML Processor Package
Process academic papers using GROBID with resume capability
"""

from .processor import GrobidProcessor
from .config import Config

__version__ = "1.0.0"
__all__ = ["GrobidProcessor", "Config"]

"""
Nougat OCR Processor Package
Process academic papers using Nougat OCR with resume capability
"""

from .processor import NougatProcessor
from .config import Config

__version__ = "1.0.0"
__all__ = ["NougatProcessor", "Config"]

"""
Generate Prompts Package
Generate Type 1 and Type 2 LLM prompt text files from citation context JSONs.
"""

from .processor import PromptGeneratorProcessor
from .config import Config

__version__ = "1.0.0"
__all__ = ["PromptGeneratorProcessor", "Config"]

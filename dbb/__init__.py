"""DuckDB Broadcast Briefs - YouTube Podcast Archive System."""

__version__ = "0.1.0"
__author__ = "Kosi Uzodinma"
__description__ = "Local YouTube podcast archive with API-based transcription and local summarization"

from dbb.config import Config, load_config
from dbb.db import DatabaseManager

__all__ = ["Config", "load_config", "DatabaseManager", "__version__"]

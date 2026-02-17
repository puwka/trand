"""Application configuration."""

from .main import Settings, settings
from .ingestion import IngestionSettings, ingestion_settings

__all__ = [
    "Settings",
    "settings",
    "IngestionSettings",
    "ingestion_settings",
]

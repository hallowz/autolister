"""
Web scrapers for discovering PDF manuals
"""
from .base import BaseScraper
from .search_engine import GoogleScraper, BingScraper
from .forums import ForumScraper
from .manual_sites import ManualSiteScraper
from .gdrive import GoogleDriveExtractor

__all__ = [
    'BaseScraper',
    'GoogleScraper',
    'BingScraper',
    'ForumScraper',
    'ManualSiteScraper',
    'GoogleDriveExtractor',
]

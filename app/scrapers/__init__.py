"""
Web scrapers for discovering PDF manuals
"""
from .base import BaseScraper
from .search_engine import GoogleScraper, BingScraper
from .duckduckgo import DuckDuckGoScraper
from .forums import ForumScraper
from .manual_sites import ManualSiteScraper
from .gdrive import GoogleDriveExtractor
from .multi_site_scraper import MultiSiteScraper

__all__ = [
    'BaseScraper',
    'GoogleScraper',
    'BingScraper',
    'DuckDuckGoScraper',
    'ForumScraper',
    'ManualSiteScraper',
    'GoogleDriveExtractor',
    'MultiSiteScraper',
]

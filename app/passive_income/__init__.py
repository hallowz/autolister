"""
Passive Income Dashboard - Multi-platform autonomous listing system

This module provides:
- Multi-platform listing management (Etsy, Gumroad, Payhip, eBay, etc.)
- Autonomous operation with AI-powered decision making
- Human intervention queue for actions requiring manual input
- Revenue tracking and analytics
- SEO-optimized listing generation
- Auto-scraping agent with AI niche discovery
"""
from app.passive_income.database import (
    Platform, PlatformListing, ActionQueue, Revenue, Setting,
    PassiveIncomeManager, NicheDiscovery, MarketResearch, AutoScrapingState
)
from app.passive_income.platforms import PlatformRegistry
from app.passive_income.agent import AutonomousAgent
from app.passive_income.auto_scraping_agent import AutoScrapingAgent

__all__ = [
    'Platform', 'PlatformListing', 'ActionQueue', 'Revenue', 'Setting',
    'PassiveIncomeManager', 'PlatformRegistry', 'AutonomousAgent',
    'NicheDiscovery', 'MarketResearch', 'AutoScrapingState', 'AutoScrapingAgent'
]

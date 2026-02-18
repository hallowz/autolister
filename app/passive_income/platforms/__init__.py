"""
Platform integrations for passive income listing
"""
from app.passive_income.platforms.base import BasePlatform
from app.passive_income.platforms.registry import PlatformRegistry
from app.passive_income.platforms.etsy import EtsyPlatform
from app.passive_income.platforms.gumroad import GumroadPlatform
from app.passive_income.platforms.payhip import PayhipPlatform

__all__ = [
    'BasePlatform', 'PlatformRegistry',
    'EtsyPlatform', 'GumroadPlatform', 'PayhipPlatform'
]

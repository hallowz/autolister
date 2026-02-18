"""
Payhip Platform Integration
Free digital download platform - No API, requires manual listing
"""
from typing import Dict, List
from app.passive_income.platforms.base import BasePlatform, PlatformStatus, ListingResult


class PayhipPlatform(BasePlatform):
    """Payhip platform - requires manual listing (no public API)"""
    
    name = "payhip"
    display_name = "Payhip"
    platform_type = "digital_download"
    supports_api_listing = False  # No public API
    supports_digital_downloads = True
    is_free = True
    
    max_title_length = 100
    max_description_length = 10000
    required_credentials = []
    
    def check_status(self) -> PlatformStatus:
        return PlatformStatus(
            is_configured=True,
            is_connected=True,
            requires_auth=False,
            error="Payhip has no API - manual listing required"
        )
    
    def create_listing(self, title: str, description: str, price: float, 
                       file_path: str = None, images: List[str] = None, 
                       tags: List[str] = None, **kwargs) -> ListingResult:
        return self.requires_manual_action(
            'manual_listing',
            "Payhip does not have a public API. Please create listing manually.",
            {
                'url': 'https://payhip.com/dashboard',
                'title': title,
                'description': description[:500],
                'price': price,
                'suggested_tags': tags or []
            }
        )
    
    def update_listing(self, listing_id: str, title: str = None, 
                       description: str = None, price: float = None, **kwargs) -> ListingResult:
        return self.requires_manual_action(
            'manual_update',
            "Payhip requires manual updates through their dashboard.",
            {'listing_id': listing_id, 'url': 'https://payhip.com/dashboard'}
        )
    
    def delete_listing(self, listing_id: str) -> ListingResult:
        return self.requires_manual_action(
            'manual_delete',
            "Payhip requires manual deletion through their dashboard.",
            {'listing_id': listing_id, 'url': 'https://payhip.com/dashboard'}
        )
    
    def get_listing(self, listing_id: str) -> Dict:
        return {'error': 'No API access', 'url': f'https://payhip.com/b/{listing_id}'}
    
    def get_sales(self, days: int = 30) -> List[Dict]:
        return []  # No API access

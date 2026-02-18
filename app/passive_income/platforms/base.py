"""
Base platform class for all listing platforms
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class ListingResult:
    """Result of a listing operation"""
    
    def __init__(
        self,
        success: bool,
        listing_id: str = None,
        listing_url: str = None,
        error: str = None,
        requires_action: bool = False,
        action_type: str = None,
        action_data: Dict = None
    ):
        self.success = success
        self.listing_id = listing_id
        self.listing_url = listing_url
        self.error = error
        self.requires_action = requires_action
        self.action_type = action_type
        self.action_data = action_data or {}
    
    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'listing_id': self.listing_id,
            'listing_url': self.listing_url,
            'error': self.error,
            'requires_action': self.requires_action,
            'action_type': self.action_type,
            'action_data': self.action_data
        }


class PlatformStatus:
    """Status of a platform connection"""
    
    def __init__(
        self,
        is_configured: bool = False,
        is_connected: bool = False,
        requires_auth: bool = False,
        auth_url: str = None,
        error: str = None,
        rate_limit_remaining: int = None,
        rate_limit_reset: datetime = None
    ):
        self.is_configured = is_configured
        self.is_connected = is_connected
        self.requires_auth = requires_auth
        self.auth_url = auth_url
        self.error = error
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset = rate_limit_reset
    
    def to_dict(self) -> Dict:
        return {
            'is_configured': self.is_configured,
            'is_connected': self.is_connected,
            'requires_auth': self.requires_auth,
            'auth_url': self.auth_url,
            'error': self.error,
            'rate_limit_remaining': self.rate_limit_remaining,
            'rate_limit_reset': self.rate_limit_reset.isoformat() if self.rate_limit_reset else None
        }


class BasePlatform(ABC):
    """
    Abstract base class for all listing platforms
    
    Each platform must implement:
    - check_status(): Check if the platform is connected and configured
    - create_listing(): Create a new listing
    - update_listing(): Update an existing listing
    - delete_listing(): Delete/remove a listing
    - get_listing(): Get listing details
    - get_sales(): Get sales/revenue data
    """
    
    # Platform metadata (override in subclasses)
    name: str = "base"
    display_name: str = "Base Platform"
    platform_type: str = "digital_download"
    supports_api_listing: bool = False
    supports_digital_downloads: bool = True
    is_free: bool = True
    
    # Rate limiting defaults
    rate_limit_requests: int = 100
    rate_limit_period: int = 3600  # seconds
    
    def __init__(self, credentials: Dict = None, config: Dict = None):
        """
        Initialize platform with credentials and configuration
        
        Args:
            credentials: Platform-specific credentials (API keys, tokens, etc.)
            config: Platform-specific configuration options
        """
        self.credentials = credentials or {}
        self.config = config or {}
        self._last_request_time = None
        self._request_count = 0
    
    @abstractmethod
    def check_status(self) -> PlatformStatus:
        """
        Check if the platform is properly configured and connected
        
        Returns:
            PlatformStatus with connection details
        """
        pass
    
    @abstractmethod
    def create_listing(
        self,
        title: str,
        description: str,
        price: float,
        file_path: str = None,
        images: List[str] = None,
        tags: List[str] = None,
        **kwargs
    ) -> ListingResult:
        """
        Create a new listing on the platform
        
        Args:
            title: Listing title
            description: Listing description
            price: Listing price
            file_path: Path to digital file (for digital downloads)
            images: List of image file paths
            tags: List of tags/keywords
            **kwargs: Platform-specific options
            
        Returns:
            ListingResult with success status and listing details
        """
        pass
    
    @abstractmethod
    def update_listing(
        self,
        listing_id: str,
        title: str = None,
        description: str = None,
        price: float = None,
        **kwargs
    ) -> ListingResult:
        """
        Update an existing listing
        
        Args:
            listing_id: Platform's listing ID
            title: New title (optional)
            description: New description (optional)
            price: New price (optional)
            **kwargs: Platform-specific options
            
        Returns:
            ListingResult with success status
        """
        pass
    
    @abstractmethod
    def delete_listing(self, listing_id: str) -> ListingResult:
        """
        Delete/remove a listing from the platform
        
        Args:
            listing_id: Platform's listing ID
            
        Returns:
            ListingResult with success status
        """
        pass
    
    @abstractmethod
    def get_listing(self, listing_id: str) -> Dict:
        """
        Get details of a specific listing
        
        Args:
            listing_id: Platform's listing ID
            
        Returns:
            Dictionary with listing details
        """
        pass
    
    @abstractmethod
    def get_sales(self, days: int = 30) -> List[Dict]:
        """
        Get sales/revenue data from the platform
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of sale records
        """
        pass
    
    def generate_seo_title(self, base_title: str, metadata: Dict = None) -> str:
        """
        Generate an SEO-optimized title for the platform
        
        Args:
            base_title: Base title from the product
            metadata: Additional metadata (manufacturer, model, year, etc.)
            
        Returns:
            SEO-optimized title string
        """
        # Default implementation - can be overridden per platform
        title = base_title
        
        # Add platform-specific prefixes/suffixes
        if self.name == 'etsy':
            if 'digital' not in title.lower():
                title += ' | Digital Download PDF'
        elif self.name == 'gumroad':
            if 'pdf' not in title.lower():
                title += ' [PDF]'
        
        # Truncate to platform limits
        max_length = getattr(self, 'max_title_length', 140)
        if len(title) > max_length:
            title = title[:max_length-3] + '...'
        
        return title
    
    def generate_tags(self, keywords: List[str], metadata: Dict = None) -> List[str]:
        """
        Generate platform-specific tags from keywords and metadata
        
        Args:
            keywords: List of keywords to convert to tags
            metadata: Additional metadata for context
            
        Returns:
            List of tags formatted for the platform
        """
        max_tags = getattr(self, 'max_tags', 13)
        max_tag_length = getattr(self, 'max_tag_length', 20)
        
        tags = []
        for keyword in keywords[:max_tags]:
            # Clean and truncate tag
            tag = keyword.strip().lower()
            if len(tag) > max_tag_length:
                tag = tag[:max_tag_length]
            if tag and tag not in tags:
                tags.append(tag)
        
        return tags
    
    def validate_credentials(self) -> tuple:
        """
        Validate that required credentials are present
        
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        required_fields = getattr(self, 'required_credentials', [])
        missing = []
        
        for field in required_fields:
            if not self.credentials.get(field):
                missing.append(field)
        
        return len(missing) == 0, missing
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits
        
        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.utcnow()
        
        if self._last_request_time:
            elapsed = (now - self._last_request_time).total_seconds()
            
            if elapsed < self.rate_limit_period:
                if self._request_count >= self.rate_limit_requests:
                    return False
            else:
                # Reset counter for new period
                self._request_count = 0
        
        return True
    
    def _record_request(self):
        """Record a request for rate limiting"""
        self._request_count += 1
        self._last_request_time = datetime.utcnow()
    
    def requires_manual_action(self, action_type: str, reason: str, data: Dict = None) -> ListingResult:
        """
        Create a ListingResult indicating manual action is required
        
        Args:
            action_type: Type of action needed
            reason: Why manual action is needed
            data: Additional data for the action
            
        Returns:
            ListingResult with requires_action=True
        """
        return ListingResult(
            success=False,
            requires_action=True,
            action_type=action_type,
            error=reason,
            action_data=data or {}
        )
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"

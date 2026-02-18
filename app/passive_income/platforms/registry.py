"""
Platform Registry - Manages all platform integrations
"""
from typing import Dict, List, Type, Optional
from app.passive_income.platforms.base import BasePlatform


class PlatformRegistry:
    """
    Central registry for all platform integrations
    
    Usage:
        # Register a platform
        PlatformRegistry.register(GumroadPlatform)
        
        # Get a platform instance
        gumroad = PlatformRegistry.get('gumroad', credentials={...})
        
        # List all platforms
        platforms = PlatformRegistry.list_platforms()
    """
    
    _platforms: Dict[str, Type[BasePlatform]] = {}
    _instances: Dict[str, BasePlatform] = {}
    
    @classmethod
    def register(cls, platform_class: Type[BasePlatform]) -> None:
        """
        Register a platform class
        
        Args:
            platform_class: The platform class to register
        """
        instance = platform_class()
        cls._platforms[instance.name] = platform_class
        print(f"Registered platform: {instance.name}")
    
    @classmethod
    def get(
        cls,
        name: str,
        credentials: Dict = None,
        config: Dict = None,
        use_cache: bool = True
    ) -> Optional[BasePlatform]:
        """
        Get a platform instance
        
        Args:
            name: Platform name
            credentials: Platform credentials
            config: Platform configuration
            use_cache: Whether to use cached instance
            
        Returns:
            Platform instance or None if not found
        """
        if name not in cls._platforms:
            return None
        
        # Create cache key based on credentials
        cache_key = f"{name}_{hash(str(credentials))}"
        
        if use_cache and cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Create new instance
        platform_class = cls._platforms[name]
        instance = platform_class(credentials=credentials, config=config)
        
        if use_cache:
            cls._instances[cache_key] = instance
        
        return instance
    
    @classmethod
    def list_platforms(cls) -> List[Dict]:
        """
        List all registered platforms with their metadata
        
        Returns:
            List of platform info dictionaries
        """
        platforms = []
        
        for name, platform_class in cls._platforms.items():
            instance = platform_class()
            platforms.append({
                'name': instance.name,
                'display_name': instance.display_name,
                'platform_type': instance.platform_type,
                'supports_api_listing': instance.supports_api_listing,
                'supports_digital_downloads': instance.supports_digital_downloads,
                'is_free': instance.is_free
            })
        
        return platforms
    
    @classmethod
    def get_platforms_by_type(cls, platform_type: str) -> List[Type[BasePlatform]]:
        """
        Get all platforms of a specific type
        
        Args:
            platform_type: Type to filter by ('digital_download', 'marketplace', etc.)
            
        Returns:
            List of matching platform classes
        """
        matching = []
        
        for platform_class in cls._platforms.values():
            instance = platform_class()
            if instance.platform_type == platform_type:
                matching.append(platform_class)
        
        return matching
    
    @classmethod
    def get_free_platforms(cls) -> List[Type[BasePlatform]]:
        """
        Get all platforms that are free (no upfront costs)
        
        Returns:
            List of free platform classes
        """
        free = []
        
        for platform_class in cls._platforms.values():
            instance = platform_class()
            if instance.is_free:
                free.append(platform_class)
        
        return free
    
    @classmethod
    def get_api_capable_platforms(cls) -> List[Type[BasePlatform]]:
        """
        Get all platforms that support API listing
        
        Returns:
            List of platforms with API listing support
        """
        api_capable = []
        
        for platform_class in cls._platforms.values():
            instance = platform_class()
            if instance.supports_api_listing:
                api_capable.append(platform_class)
        
        return api_capable
    
    @classmethod
    def clear_cache(cls):
        """Clear cached platform instances"""
        cls._instances.clear()
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a platform is registered"""
        return name in cls._platforms


def auto_register_platforms():
    """
    Auto-register all platform classes defined in the platforms module
    """
    from app.passive_income.platforms import (
        EtsyPlatform,
        GumroadPlatform,
        PayhipPlatform
    )
    
    # Register each platform
    for platform_class in [EtsyPlatform, GumroadPlatform, PayhipPlatform]:
        PlatformRegistry.register(platform_class)
    
    print(f"Auto-registered {len(PlatformRegistry._platforms)} platforms")

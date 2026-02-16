"""
Configuration management for AutoLister
"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import yaml


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "AutoLister"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Scraping
    scraping_interval_hours: int = 6
    max_results_per_search: int = 20
    user_agent: str = "AutoLister/1.0"
    request_timeout: int = 30
    
    # Google Custom Search API
    google_api_key: str = ""
    google_cx: str = ""
    
    # Bing Search API
    bing_api_key: str = ""
    
    # Etsy API
    etsy_api_key: str = ""
    etsy_api_secret: str = ""
    etsy_access_token: str = ""
    etsy_access_token_secret: str = ""
    etsy_shop_id: str = ""
    etsy_default_price: float = 4.99
    etsy_default_quantity: int = 9999
    
    # Processing
    max_pdf_size_mb: int = 50
    image_dpi: int = 150
    image_format: str = "jpeg"
    main_image_page: int = 1
    additional_image_pages: List[int] = Field(default_factory=lambda: [2, 3, 4])
    
    # Database
    database_path: str = "./data/autolister.db"
    
    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    
    # Redis/Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/autolister.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class SearchConfig:
    """Search terms and equipment categories configuration"""
    
    def __init__(self, config_path: str = "config/search_terms.yaml"):
        self.config_path = Path(config_path)
        self.equipment_categories = []
        self._load_config()
    
    def _load_config(self):
        """Load search terms from YAML file"""
        if not self.config_path.exists():
            self._create_default_config()
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.equipment_categories = config.get('equipment_categories', [])
    
    def _create_default_config(self):
        """Create default search terms configuration"""
        default_config = {
            'equipment_categories': [
                {
                    'name': 'ATV/UTV',
                    'brands': ['Honda', 'Yamaha', 'Polaris', 'Suzuki', 'Kawasaki', 'Can-Am'],
                    'types': ['ATV', 'UTV', 'Side by Side', 'Quad'],
                    'keywords': ['manual', 'service manual', 'owner manual', 'repair manual']
                },
                {
                    'name': 'Lawnmowers',
                    'brands': ['Toro', 'Craftsman', 'John Deere', 'Honda', 'Husqvarna'],
                    'types': ['Lawn Mower', 'Riding Mower', 'Push Mower', 'Zero Turn'],
                    'keywords': ['manual', 'service manual', 'owner manual']
                },
                {
                    'name': 'Tractors',
                    'brands': ['John Deere', 'Kubota', 'Massey Ferguson', 'New Holland'],
                    'types': ['Tractor', 'Compact Tractor', 'Farm Tractor'],
                    'keywords': ['manual', 'service manual', 'operator manual']
                },
                {
                    'name': 'Generators',
                    'brands': ['Honda', 'Generac', 'Champion', 'Westinghouse'],
                    'types': ['Generator', 'Portable Generator', 'Inverter Generator'],
                    'keywords': ['manual', 'owner manual', 'service manual']
                }
            ]
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def get_search_queries(self) -> List[str]:
        """Generate all possible search queries from configuration"""
        queries = []
        for category in self.equipment_categories:
            for brand in category['brands']:
                for type_ in category['types']:
                    for keyword in category['keywords']:
                        queries.append(f"{brand} {type_} {keyword} pdf")
        return queries
    
    def get_category_by_name(self, name: str) -> dict:
        """Get a specific category by name"""
        for category in self.equipment_categories:
            if category['name'] == name:
                return category
        return None


# Global settings instance
settings = Settings()

# Global search config instance
search_config = SearchConfig()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def get_search_config() -> SearchConfig:
    """Get the global search config instance"""
    return search_config

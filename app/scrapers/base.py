"""
Base scraper class for all scrapers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
from urllib.parse import urlparse


@dataclass
class PDFResult:
    """Result from a scraper containing PDF URL and metadata"""
    url: str
    source_type: str
    title: Optional[str] = None
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.user_agent = self.config.get('user_agent', 'AutoLister/1.0')
        self.timeout = self.config.get('timeout', 30)
        self.max_results = self.config.get('max_results', 20)
    
    @abstractmethod
    def search(self, query: str) -> List[PDFResult]:
        """
        Search for PDF manuals based on the query
        
        Args:
            query: Search query string
            
        Returns:
            List of PDFResult objects
        """
        pass
    
    def is_pdf_url(self, url: str) -> bool:
        """
        Check if URL points to a PDF file
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be a PDF
        """
        url_lower = url.lower()
        return (
            url_lower.endswith('.pdf') or
            'filetype:pdf' in url_lower or
            'application/pdf' in url_lower
        )
    
    def extract_pdf_metadata(self, url: str, title: str = None) -> Dict:
        """
        Extract metadata from URL and title
        
        Args:
            url: PDF URL
            title: Optional title from source
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'manufacturer': None,
            'model': None,
            'year': None,
            'equipment_type': None
        }
        
        # Extract from title
        if title:
            title_lower = title.lower()
            
            # Try to extract manufacturer from common brands
            brands = [
                'honda', 'yamaha', 'polaris', 'suzuki', 'kawasaki', 'can-am',
                'toro', 'craftsman', 'john deere', 'husqvarna',
                'kubota', 'massey ferguson', 'new holland',
                'generac', 'champion', 'westinghouse'
            ]
            
            for brand in brands:
                if brand in title_lower:
                    metadata['manufacturer'] = brand.title()
                    break
            
            # Try to extract year (4 digits)
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            if year_match:
                metadata['year'] = year_match.group()
        
        # Extract from URL
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        
        # Look for model information in path
        for part in path_parts:
            if re.match(r'^[a-z]{2,}\d+', part.lower()):
                # Likely a model (letters followed by numbers)
                metadata['model'] = part.upper()
        
        return metadata
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing tracking parameters
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        parsed = urlparse(url)
        
        # Remove common tracking parameters
        query_params = []
        for param in parsed.query.split('&'):
            if param and not any(x in param.lower() for x in ['utm_', 'ref_', 'source']):
                query_params.append(param)
        
        normalized = parsed._replace(
            query='&'.join(query_params) if query_params else '',
            fragment=''
        )
        
        return normalized.geturl()

"""
Search engine scrapers (Google and Bing)
"""
import requests
from typing import List
from .base import BaseScraper, PDFResult


class GoogleScraper(BaseScraper):
    """Google Custom Search API scraper"""
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.api_key = self.config.get('google_api_key', '')
        self.cx = self.config.get('google_cx', '')
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    def search(self, query: str) -> List[PDFResult]:
        """
        Search Google Custom Search API for PDF manuals
        
        Args:
            query: Search query string
            
        Returns:
            List of PDFResult objects
        """
        if not self.api_key or not self.cx:
            print("Warning: Google API key or CX not configured")
            return []
        
        results = []
        
        try:
            # Add PDF file type to query
            pdf_query = f"{query} filetype:pdf"
            
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': pdf_query,
                'num': min(self.max_results, 10)  # API limit is 10 per request
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get('items', []):
                url = item.get('link', '')
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                
                if self.is_pdf_url(url):
                    metadata = self.extract_pdf_metadata(url, title)
                    
                    results.append(PDFResult(
                        url=self.normalize_url(url),
                        source_type='search',
                        title=title or snippet[:100],
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    ))
                    
                    if len(results) >= self.max_results:
                        break
        
        except requests.RequestException as e:
            print(f"Google API error: {e}")
        except Exception as e:
            print(f"Google scraper error: {e}")
        
        return results


class BingScraper(BaseScraper):
    """Bing Search API scraper"""
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.api_key = self.config.get('bing_api_key', '')
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
    
    def search(self, query: str) -> List[PDFResult]:
        """
        Search Bing API for PDF manuals
        
        Args:
            query: Search query string
            
        Returns:
            List of PDFResult objects
        """
        if not self.api_key:
            print("Warning: Bing API key not configured")
            return []
        
        results = []
        
        try:
            # Add PDF file type to query
            pdf_query = f"{query} filetype:pdf"
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'User-Agent': self.user_agent
            }
            
            params = {
                'q': pdf_query,
                'count': min(self.max_results, 50)
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get('webPages', {}).get('value', []):
                url = item.get('url', '')
                title = item.get('name', '')
                snippet = item.get('snippet', '')
                
                if self.is_pdf_url(url):
                    metadata = self.extract_pdf_metadata(url, title)
                    
                    results.append(PDFResult(
                        url=self.normalize_url(url),
                        source_type='search',
                        title=title or snippet[:100],
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    ))
                    
                    if len(results) >= self.max_results:
                        break
        
        except requests.RequestException as e:
            print(f"Bing API error: {e}")
        except Exception as e:
            print(f"Bing scraper error: {e}")
        
        return results

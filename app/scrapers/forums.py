"""
Forum scraper for equipment forums
"""
import requests
from bs4 import BeautifulSoup
from typing import List
from .base import BaseScraper, PDFResult


class ForumScraper(BaseScraper):
    """Scraper for equipment forums (ATV, lawnmower, etc.)"""
    
    # Common forum URLs to search
    FORUM_SITES = [
        {
            'name': 'ATVConnection',
            'base_url': 'https://www.atvconnection.com',
            'search_path': '/search'
        },
        {
            'name': 'LawnMowerForum',
            'base_url': 'https://www.lawnmowerforum.com',
            'search_path': '/search'
        },
        {
            'name': 'MyTractorForum',
            'base_url': 'https://www.mytractorforum.com',
            'search_path': '/search'
        }
    ]
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.forum_sites = self.config.get('forum_sites', self.FORUM_SITES)
    
    def search(self, query: str) -> List[PDFResult]:
        """
        Search forums for PDF manual links
        
        Args:
            query: Search query string
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        for forum in self.forum_sites:
            try:
                forum_results = self._search_forum(forum, query)
                results.extend(forum_results)
                
                if len(results) >= self.max_results:
                    break
            except Exception as e:
                print(f"Error searching forum {forum['name']}: {e}")
                continue
        
        return results[:self.max_results]
    
    def _search_forum(self, forum: dict, query: str) -> List[PDFResult]:
        """
        Search a specific forum for PDF links
        
        Args:
            forum: Forum configuration dict
            query: Search query
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        try:
            # Note: This is a simplified implementation
            # Real forum scraping would need to handle authentication,
            # CSRF tokens, and forum-specific search parameters
            
            search_url = f"{forum['base_url']}{forum['search_path']}"
            
            params = {
                'q': query,
                'type': 'posts'
            }
            
            response = requests.get(
                search_url,
                params=params,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for PDF links in search results
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Check if it's a PDF link
                if self.is_pdf_url(href):
                    title = link.get_text(strip=True)
                    metadata = self.extract_pdf_metadata(href, title)
                    
                    results.append(PDFResult(
                        url=self.normalize_url(href),
                        source_type='forum',
                        source_name=forum['name'],
                        title=title,
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    ))
            
            # Also look for Google Drive links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'drive.google.com' in href or 'docs.google.com' in href:
                    # This will be processed by GoogleDriveExtractor
                    pass
        
        except requests.RequestException as e:
            print(f"Request error for {forum['name']}: {e}")
        except Exception as e:
            print(f"Error parsing {forum['name']}: {e}")
        
        return results

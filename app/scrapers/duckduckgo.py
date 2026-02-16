"""
DuckDuckGo scraper for searching PDF manuals
DuckDuckGo is free and doesn't require API keys
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import urllib.parse
import time
import random
from .base import BaseScraper, PDFResult


class DuckDuckGoScraper(BaseScraper):
    """Scraper for DuckDuckGo search results"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = "https://html.duckduckgo.com/html/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def search(self, query: str, max_results: int = 20) -> List[PDFResult]:
        """
        Search DuckDuckGo for PDF manuals
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        try:
            # Add "pdf" to query if not already present
            if 'pdf' not in query.lower():
                search_query = f"{query} pdf"
            else:
                search_query = query
            
            # Prepare search parameters
            params = {
                'q': search_query,
                'kl': 'us-en',  # Region/language
                'num': max_results
            }
            
            # Make request to DuckDuckGo
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.config.get('request_timeout', 30)
            )
            response.raise_for_status()
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            result_divs = soup.find_all('div', class_='result')
            
            # Try to find direct PDF links within the result div
            for div in result_divs:
                # Look for direct PDF links in the result content
                pdf_links = div.find_all('a', href=lambda x: x and x.get('href', '').lower().endswith('.pdf'))
                if pdf_links:
                    # Use the first direct PDF link found
                    url = pdf_links[0].get('href', '')
                    title = pdf_links[0].get_text(strip=True)
                    # Extract snippet from the result
                    snippet_elem = div.find('a', class_='result__snippet')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    # Extract source
                    source_elem = div.find('span', class_='result__url')
                    source = source_elem.get_text(strip=True) if source_elem else self._extract_domain(url)
                    
                    # VALIDATE: Only include if URL appears to be a downloadable PDF
                    if not self._is_valid_pdf_url(url, source):
                        continue
                    
                    # Extract metadata
                    metadata = self.extract_pdf_metadata(url, title)
                    metadata['search_engine'] = 'duckduckgo'
                    metadata['query'] = search_query
                    metadata['description'] = snippet
                    
                    # Create search result
                    result = PDFResult(
                        url=url,
                        source_type='duckduckgo',
                        title=title,
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    )
                    
                    results.append(result)
                    
                    # Stop if we have enough results
                    if len(results) >= max_results:
                        break
            
            # Only process result_divs if we didn't find direct PDF links
            if not results:
                # Fall back to original parsing if no direct PDF links found
                for div in result_divs:
                    try:
                        # Extract title
                        title_elem = div.find('a', class_='result__a')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                        
                        # Extract snippet/description
                        snippet_elem = div.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        # Extract source
                        source_elem = div.find('span', class_='result__url')
                        source = source_elem.get_text(strip=True) if source_elem else self._extract_domain(url)
                        
                        # VALIDATE: Only include if URL appears to be a downloadable PDF
                        if not self._is_valid_pdf_url(url, source):
                            continue
                        
                        # Extract metadata
                        metadata = self.extract_pdf_metadata(url, title)
                        metadata['search_engine'] = 'duckduckgo'
                        metadata['query'] = search_query
                        metadata['description'] = snippet
                        
                        # Create search result
                        result = PDFResult(
                            url=url,
                            source_type='duckduckgo',
                            title=title,
                            equipment_type=metadata.get('equipment_type'),
                            manufacturer=metadata.get('manufacturer'),
                            model=metadata.get('model'),
                            year=metadata.get('year'),
                            metadata=metadata
                        )
                        
                        results.append(result)
                        
                        # Stop if we have enough results
                        if len(results) >= max_results:
                            break
                            
                    except Exception as e:
                        print(f"Error parsing result: {e}")
                        continue
            
            print(f"DuckDuckGo search returned {len(results)} results for query: {query}")
            
        except requests.RequestException as e:
            print(f"DuckDuckGo search request failed: {e}")
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return 'unknown'
    
    def _is_valid_pdf_url(self, url: str, source: str) -> bool:
        """
        Validate if URL points to a downloadable PDF file
        
        Only returns True if:
        1. URL ends with .pdf (direct PDF link)
        2. OR URL is from a known PDF/manual site
        
        This ensures only valid, downloadable PDFs are shown for approval.
        """
        url_lower = url.lower()
        source_lower = source.lower()
        
        # Direct PDF link - most reliable
        if url_lower.endswith('.pdf'):
            return True
        
        # Known PDF/manual sites that host downloadable files
        pdf_sites = [
            'manualslib', 'manualsdir', 'emanualonline',
            'manual', 'service-manual', 'owner-manual',
            'repair-manual', 'workshop-manual', 'parts-manual',
            'scribd', 'issuu', 'yumpu',
            'drive.google.com', 'dropbox.com', 'mediafire.com',
            'mega.nz', '4shared.com', 'zippyshare.com'
        ]
        
        for site in pdf_sites:
            if site in url_lower or site in source_lower:
                return True
        
        # URL contains pdf indicator (less reliable but useful)
        if 'pdf' in url_lower or 'filetype=pdf' in url_lower:
            return True
        
        return False
    
    def is_pdf_link(self, url: str) -> bool:
        """Check if URL points to a PDF file"""
        return url.lower().endswith('.pdf') or 'pdf' in url.lower()
    
    def filter_pdf_results(self, results: List[PDFResult]) -> List[PDFResult]:
        """Filter results to only include PDF links or likely PDF sources"""
        pdf_results = []
        
        for result in results:
            # Direct PDF link
            if self.is_pdf_url(result.url):
                pdf_results.append(result)
            # Likely PDF source (manual sites, document repositories)
            elif self._is_likely_pdf_source(result.url, result.source_type):
                pdf_results.append(result)
        
        return pdf_results
    
    def _is_likely_pdf_source(self, url: str, source: str) -> bool:
        """Check if URL is likely to contain PDFs"""
        likely_sources = [
            'manualslib', 'manualsdir', 'emanualonline',
            'pdf', 'manual', 'service-manual', 'owner-manual',
            'repair-manual', 'workshop-manual', 'parts-manual',
            'scribd', 'issuu', 'yumpu',
            'drive.google.com', 'dropbox.com', 'mediafire.com',
            'mega.nz', '4shared.com', 'zippyshare.com'
        ]
        
        url_lower = url.lower()
        source_lower = source.lower()
        
        for keyword in likely_sources:
            if keyword in url_lower or keyword in source_lower:
                return True
        
        return False

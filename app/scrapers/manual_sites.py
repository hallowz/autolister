"""
Manual-specific website scrapers (manualslib, manualsdir, etc.)
"""
import requests
from bs4 import BeautifulSoup
from typing import List
from .base import BaseScraper, PDFResult


class ManualSiteScraper(BaseScraper):
    """Scraper for manual-specific websites"""
    
    # Common manual sites
    MANUAL_SITES = [
        {
            'name': 'ManualsLib',
            'base_url': 'https://www.manualslib.com',
            'search_path': '/search'
        },
        {
            'name': 'ManualsDir',
            'base_url': 'https://www.manualsdir.com',
            'search_path': '/search'
        },
        {
            'name': 'ManualsOnline',
            'base_url': 'https://www.manualsonline.com',
            'search_path': '/search'
        }
    ]
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.manual_sites = self.config.get('manual_sites', self.MANUAL_SITES)
    
    def search(self, query: str) -> List[PDFResult]:
        """
        Search manual sites for PDF manuals
        
        Args:
            query: Search query string
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        for site in self.manual_sites:
            try:
                site_results = self._search_manual_site(site, query)
                results.extend(site_results)
                
                if len(results) >= self.max_results:
                    break
            except Exception as e:
                print(f"Error searching manual site {site['name']}: {e}")
                continue
        
        return results[:self.max_results]
    
    def _search_manual_site(self, site: dict, query: str) -> List[PDFResult]:
        """
        Search a specific manual site
        
        Args:
            site: Site configuration dict
            query: Search query
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        try:
            search_url = f"{site['base_url']}{site['search_path']}"
            
            params = {
                'q': query
            }
            
            response = requests.get(
                search_url,
                params=params,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for PDF download links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Make absolute URL if relative
                if href.startswith('/'):
                    href = f"{site['base_url']}{href}"
                
                # Check if it's a PDF link
                if self.is_pdf_url(href):
                    title = link.get_text(strip=True)
                    metadata = self.extract_pdf_metadata(href, title)
                    
                    results.append(PDFResult(
                        url=self.normalize_url(href),
                        source_type='manual_site',
                        source_name=site['name'],
                        title=title,
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    ))
            
            # Also look for product pages that link to PDFs
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Make absolute URL if relative
                if href.startswith('/'):
                    href = f"{site['base_url']}{href}"
                
                # Check if it's a product/manual page (not a direct PDF)
                if not self.is_pdf_url(href) and '/manual/' in href.lower():
                    # Try to fetch the page and look for PDF links
                    try:
                        page_results = self._fetch_manual_page(href, site['name'])
                        results.extend(page_results)
                    except Exception:
                        continue
        
        except requests.RequestException as e:
            print(f"Request error for {site['name']}: {e}")
        except Exception as e:
            print(f"Error parsing {site['name']}: {e}")
        
        return results
    
    def _fetch_manual_page(self, url: str, site_name: str) -> List[PDFResult]:
        """
        Fetch a manual page and extract PDF links
        
        Args:
            url: URL of the manual page
            site_name: Name of the site
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for PDF download button/link
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Make absolute URL if relative
                if href.startswith('/'):
                    href = f"{url.split('/')[0]}//{url.split('/')[2]}{href}"
                
                if self.is_pdf_url(href):
                    # Try to get title from page
                    title = soup.find('h1')
                    if title:
                        title = title.get_text(strip=True)
                    else:
                        title = link.get_text(strip=True)
                    
                    metadata = self.extract_pdf_metadata(href, title)
                    
                    results.append(PDFResult(
                        url=self.normalize_url(href),
                        source_type='manual_site',
                        source_name=site_name,
                        title=title,
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    ))
                    break  # Only get the main PDF
        
        except Exception as e:
            print(f"Error fetching manual page {url}: {e}")
        
        return results

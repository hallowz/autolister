"""
DuckDuckGo scraper for searching PDF manuals
DuckDuckGo is free and doesn't require API keys
"""
import re
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
            query: Search query string (can contain OR for multiple searches)
            max_results: Maximum number of results to return
            
        Returns:
            List of PDFResult objects
        """
        results = []
        seen_urls = set()  # Track URLs to avoid duplicates
        
        # Split query by OR (case-insensitive) and search each term separately
        queries_to_search = []
        if ' OR ' in query.upper():
            # Split by OR and strip whitespace
            queries_to_search = [q.strip() for q in query.split(' OR ')]
        else:
            queries_to_search = [query]
        
        # Calculate results per query (distribute max_results evenly)
        results_per_query = max(1, max_results // len(queries_to_search))
        
        for search_query in queries_to_search:
            # Remove filetype:pdf operator if present (DuckDuckGo HTML doesn't support it)
            search_query = re.sub(r'\bfiletype:pdf\b', '', search_query, flags=re.IGNORECASE)
            search_query = search_query.strip()
            
            # Add "pdf" to query if not already present
            if 'pdf' not in search_query.lower():
                search_query_with_pdf = f"{search_query} pdf"
            else:
                search_query_with_pdf = search_query
            
            try:
                print(f"[DuckDuckGo] Searching for: {search_query_with_pdf}")
                
                # Prepare search parameters
                params = {
                    'q': search_query_with_pdf,
                    'kl': 'us-en',  # Region/language
                    'num': results_per_query
                }
                
                # Make request to DuckDuckGo
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=self.config.get('request_timeout', 30)
                )
                response.raise_for_status()
                print(f"[DuckDuckGo] Response status: {response.status_code}")
                
                # Parse HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                result_divs = soup.find_all('div', class_='result')
                
                # Process each search result
                for div in result_divs:
                    try:
                        # Extract title and URL from the result
                        title_elem = div.find('a', class_='result__a')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        page_url = title_elem.get('href', '')
                        
                        if not page_url:
                            continue
                        
                        # Decode DuckDuckGo redirect URLs
                        page_url = self._decode_ddg_url(page_url)
                        
                        # Extract snippet/description
                        snippet_elem = div.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        # Extract source
                        source_elem = div.find('span', class_='result__url')
                        source = source_elem.get_text(strip=True) if source_elem else self._extract_domain(page_url)
                        
                        # Check if this is a direct PDF link
                        if page_url.lower().endswith('.pdf'):
                            # Direct PDF link - add it directly
                            pdf_url = page_url
                            pdf_title = title
                            print(f"[DuckDuckGo] Found direct PDF: {pdf_url}")
                        else:
                            # HTML page - fetch it and extract PDF links
                            print(f"[DuckDuckGo] Fetching page to extract PDFs: {page_url}")
                            pdf_links = self._extract_pdf_links_from_page(page_url)
                            if not pdf_links:
                                print(f"[DuckDuckGo] No PDF links found on page: {page_url}")
                                continue
                            
                            # Use the first PDF link found
                            pdf_url = pdf_links[0]
                            pdf_title = title
                            print(f"[DuckDuckGo] Found PDF link: {pdf_url}")
                        
                        # VALIDATE: Only include if URL is a downloadable PDF
                        if not self._is_valid_pdf_url(pdf_url, source):
                            continue
                        
                        # Extract metadata
                        metadata = self.extract_pdf_metadata(pdf_url, pdf_title)
                        metadata['search_engine'] = 'duckduckgo'
                        metadata['query'] = search_query
                        metadata['description'] = snippet
                        metadata['source_page'] = page_url
                        
                        # Create search result
                        result = PDFResult(
                            url=pdf_url,
                            source_type='duckduckgo',
                            title=pdf_title,
                            equipment_type=metadata.get('equipment_type'),
                            manufacturer=metadata.get('manufacturer'),
                            model=metadata.get('model'),
                            year=metadata.get('year'),
                            metadata=metadata
                        )
                        
                        # Only add if we haven't seen this URL before
                        if result.url not in seen_urls:
                            results.append(result)
                            seen_urls.add(result.url)
                    
                        # Stop if we have enough results
                        if len(results) >= max_results:
                            break
                    
                    except Exception as e:
                        print(f"Error parsing result: {e}")
                        continue
                
                print(f"DuckDuckGo search returned {len(results)} results for query: {search_query_with_pdf}")
            
            except requests.RequestException as e:
                print(f"[DuckDuckGo] Search request failed for query '{search_query_with_pdf}': {e}")
            except Exception as e:
                print(f"[DuckDuckGo] Search error for query '{search_query_with_pdf}': {e}")
                import traceback
                traceback.print_exc()
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        return results
    
    def _decode_ddg_url(self, url: str) -> str:
        """
        Decode DuckDuckGo redirect URLs
        
        DuckDuckGo uses URLs like: //duckduckgo.com/l/?uddg=URL_ENCODED
        We need to decode the uddg parameter to get the actual URL.
        """
        try:
            # Check if this is a DuckDuckGo redirect URL
            if 'duckduckgo.com/l/' in url:
                # Extract the uddg parameter
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url)
                if parsed.query:
                    params = parse_qs(parsed.query)
                    uddg = params.get('uddg', [''])[0]
                    if uddg:
                        # URL decode the uddg parameter
                        from urllib.parse import unquote
                        return unquote(uddg)
            return url
        except Exception as e:
            print(f"Error decoding DDG URL: {e}")
            return url
    
    def _extract_pdf_links_from_page(self, url: str) -> List[str]:
        """
        Fetch a page and extract all PDF links from it
        
        Args:
            url: URL of the page to fetch
            
        Returns:
            List of PDF URLs found on the page
        """
        pdf_links = []
        
        try:
            print(f"[DuckDuckGo] Fetching page: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            print(f"[DuckDuckGo] Page fetched successfully, status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links that end with .pdf
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.lower().endswith('.pdf'):
                    # Convert relative URLs to absolute
                    if not href.startswith('http'):
                        href = urllib.parse.urljoin(url, href)
                    pdf_links.append(href)
            
            # Check for open directory listings (Apache/Nginx style)
            if self._is_directory_listing(soup):
                dir_links = self._extract_directory_links(soup, url)
                pdf_links.extend(dir_links)
            
            # Check for forum attachments (common patterns)
            forum_attachments = self._extract_forum_attachments(soup, url)
            pdf_links.extend(forum_attachments)
            
        except Exception as e:
            print(f"[DuckDuckGo] Error extracting PDF links from {url}: {e}")
        
        return pdf_links
    
    def _is_directory_listing(self, soup: BeautifulSoup) -> bool:
        """Check if page is a directory listing"""
        # Look for common directory listing indicators
        title = soup.find('title')
        if title and 'index of' in title.get_text().lower():
            return True
        
        # Check for table-based directory listings
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 5:  # Multiple rows suggest directory listing
                return True
        
        # Check for common directory listing classes
        if soup.find(class_='index') or soup.find(class_='directory'):
            return True
        
        return False
    
    def _extract_directory_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract PDF links from directory listing"""
        pdf_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # Skip parent directory links and navigation
            if href.startswith('../') or href.startswith('/') or href.startswith('?'):
                continue
            
            if href.lower().endswith('.pdf'):
                # Convert relative URLs to absolute
                if not href.startswith('http'):
                    href = urllib.parse.urljoin(base_url, href)
                pdf_links.append(href)
        
        return pdf_links
    
    def _extract_forum_attachments(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract PDF attachments from forum posts"""
        pdf_links = []
        
        # Common forum attachment patterns
        attachment_selectors = [
            'a[href*="attachment"]',
            'a[href*="download"]',
            'a[href*="file"]',
            'a[class*="attachment"]',
            'a[class*="download"]',
        ]
        
        for selector in attachment_selectors:
            for link in soup.select(selector):
                href = link.get('href', '')
                if href.lower().endswith('.pdf'):
                    # Convert relative URLs to absolute
                    if not href.startswith('http'):
                        href = urllib.parse.urljoin(base_url, href)
                    if href not in pdf_links:
                        pdf_links.append(href)
        
        return pdf_links
    
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
        
        ONLY returns True if URL ends with .pdf (direct PDF link)
        
        This ensures only valid, downloadable PDFs are shown for approval.
        """
        url_lower = url.lower()
        
        # Only accept direct PDF links
        return url_lower.endswith('.pdf')
    
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

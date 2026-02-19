"""
Multi-site scraper for concurrent scraping across multiple websites
Supports directory traversal, PDF detection, and link following
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set, Callable
from urllib.parse import urljoin, urlparse, urlunparse
import re
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseScraper, PDFResult
from app.database import SessionLocal, Manual, ScrapedSite
from datetime import datetime
from urllib.parse import urlparse as url_parse
from .duckduckgo import DuckDuckGoScraper
from celery import current_app


class MultiSiteScraper(BaseScraper):
    """
    Multi-site scraper that can crawl multiple websites concurrently,
    follow links, traverse directories, and extract PDF files.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Advanced settings with defaults
        self.sites = self.config.get('sites', [])
        self.exclude_sites = self.config.get('exclude_sites', [])
        self.search_terms = self._parse_list(self.config.get('search_terms', ''))
        self.exclude_terms = self._parse_list(self.config.get('exclude_terms', ''))
        self.min_pages = self.config.get('min_pages', 5)
        self.max_pages = self.config.get('max_pages', None)
        self.min_file_size_mb = self.config.get('min_file_size_mb', None)
        self.max_file_size_mb = self.config.get('max_file_size_mb', None)
        self.follow_links = self.config.get('follow_links', True)
        self.max_depth = self.config.get('max_depth', 2)
        self.extract_directories = self.config.get('extract_directories', True)
        self.file_extensions = self._parse_list(self.config.get('file_extensions', 'pdf'))
        self.skip_duplicates = self.config.get('skip_duplicates', True)
        self.save_immediately = self.config.get('save_immediately', True)  # Save to DB immediately upon discovery
        self.job_id = self.config.get('job_id', None)  # Job ID for tracking which job created these manuals
        
        # Default exclude terms for service manual scraping
        if not self.exclude_terms:
            self.exclude_terms = ['preview', 'operator', 'operation', 'user manual', 'quick start']
        
        # Track saved URLs to avoid duplicates within the same scrape session
        self.saved_urls = set()
        
        # Batch saving for better performance
        self._pending_saves = []
        self._batch_size = self.config.get('batch_size', 10)  # Save in batches of 10
        self._db_session = None  # Reuse database session for batch operations
        self._scraped_sites_cache = {}  # Cache scraped sites to avoid repeated queries
    
    def _parse_list(self, value: Optional[str]) -> List[str]:
        """Parse comma-separated string into list"""
        if not value:
            return []
        return [item.strip().lower() for item in value.split(',') if item.strip()]
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and standardizing"""
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', parsed.query, ''))
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc
    
    def _is_excluded_site(self, url: str) -> bool:
        """Check if URL or its domain is in the exclude list"""
        if not self.exclude_sites:
            return False
        
        domain = self._extract_domain(url).lower()
        url_lower = url.lower()
        
        for excluded in self.exclude_sites:
            excluded_lower = excluded.lower().strip()
            # Check if excluded pattern matches domain or URL
            if excluded_lower in domain or excluded_lower in url_lower:
                return True
        return False
    
    def _is_valid_extension(self, url: str) -> bool:
        """Check if URL has a valid file extension"""
        url_lower = url.lower()
        for ext in self.file_extensions:
            if url_lower.endswith(f'.{ext}'):
                return True
        return False
    
    def _matches_search_terms(self, url: str, title: str = None) -> bool:
        """Check if URL or title matches search terms"""
        if not self.search_terms:
            return True
        
        text = f"{url} {title or ''}".lower()
        return any(term in text for term in self.search_terms)
    
    def _matches_exclude_terms(self, url: str, title: str = None) -> bool:
        """Check if URL or title should be excluded"""
        if not self.exclude_terms:
            return False
        
        text = f"{url} {title or ''}".lower()
        return any(term in text for term in self.exclude_terms)
    
    def _get_file_size_mb(self, url: str) -> Optional[float]:
        """Get file size in MB from URL headers (cached)"""
        # Check if we already have this URL's size cached
        if hasattr(self, '_file_size_cache') and url in self._file_size_cache:
            return self._file_size_cache[url]
        
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    # Cache the result
                    if not hasattr(self, '_file_size_cache'):
                        self._file_size_cache = {}
                    self._file_size_cache[url] = size_mb
                    return size_mb
        except Exception:
            pass
        return None
    
    def _is_pdf_directory(self, url: str, html: str) -> bool:
        """
        Check if a URL is a directory containing multiple PDFs
        This is useful for finding directories with many PDF files
        """
        soup = BeautifulSoup(html, 'html.parser')
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        return len(pdf_links) >= 3  # Consider it a PDF directory if 3+ PDFs
    
    def _get_db_session(self) -> SessionLocal:
        """Get or create a reusable database session"""
        if self._db_session is None:
            self._db_session = SessionLocal()
        return self._db_session
    
    def _flush_pending_saves(self, log_callback: Optional[Callable] = None):
        """Flush all pending saves to database in a single transaction"""
        if not self._pending_saves:
            return
        
        db = self._get_db_session()
        try:
            for result in self._pending_saves:
                # Check if URL already exists in database
                existing = db.query(Manual).filter(
                    Manual.source_url == result.url
                ).first()
                
                if existing:
                    continue
                
                # Create manual record
                manual = Manual(
                    job_id=self.job_id,
                    source_url=result.url,
                    source_type=result.source_type,
                    title=result.title,
                    equipment_type=result.equipment_type,
                    manufacturer=result.manufacturer,
                    model=result.model,
                    year=result.year,
                    status='pending',
                    processing_state='queued'
                )
                db.add(manual)
                
                # Track that this URL has been saved
                self.saved_urls.add(result.url)
            
            db.commit()
            
            # Update scraped sites in batch
            for result in self._pending_saves:
                parsed = url_parse(result.url)
                domain = parsed.netloc
                
                # Check cache first
                if domain not in self._scraped_sites_cache:
                    scraped_site = db.query(ScrapedSite).filter(
                        ScrapedSite.url == domain
                    ).first()
                    self._scraped_sites_cache[domain] = scraped_site
                
                scraped_site = self._scraped_sites_cache[domain]
                
                if scraped_site:
                    scraped_site.last_scraped_at = datetime.utcnow()
                    scraped_site.scrape_count += 1
                else:
                    try:
                        scraped_site = ScrapedSite(
                            url=domain,
                            domain=domain,
                            status='active'
                        )
                        db.add(scraped_site)
                        self._scraped_sites_cache[domain] = scraped_site
                    except Exception:
                        db.rollback()
                        # Try to get existing one
                        scraped_site = db.query(ScrapedSite).filter(
                            ScrapedSite.url == domain
                        ).first()
                        if scraped_site:
                            scraped_site.last_scraped_at = datetime.utcnow()
                            scraped_site.scrape_count += 1
                            self._scraped_sites_cache[domain] = scraped_site
            
            db.commit()
            
            # Trigger the auto-scraping agent once per batch instead of per PDF
            try:
                from app.tasks.jobs import trigger_agent_evaluation
                trigger_agent_evaluation.apply_async(countdown=2)
            except Exception as e:
                print(f"[MultiSiteScraper] Failed to trigger agent evaluation: {e}")
            
            if log_callback:
                log_callback(f"✓ Batch saved {len(self._pending_saves)} PDFs to database")
            
            self._pending_saves = []
            
        except Exception as e:
            db.rollback()
            if log_callback:
                log_callback(f"Error in batch save: {e}")
    
    def _save_pdf_to_database(self, result: PDFResult, log_callback: Optional[Callable] = None) -> bool:
        """
        Save a PDF result to the database (batched for performance)
        
        Args:
            result: PDFResult object containing PDF information
            log_callback: Optional callback function for logging
            
        Returns:
            True if saved successfully, False if already exists or error occurred
        """
        # Check if already saved in this session
        if result.url in self.saved_urls:
            return False
        
        # Add to pending saves
        self._pending_saves.append(result)
        
        # Flush if batch size reached
        if len(self._pending_saves) >= self._batch_size:
            self._flush_pending_saves(log_callback)
        elif log_callback:
            log_callback(f"Found: {result.title or result.url}")
        
        return True
    
    def _cleanup_db_session(self):
        """Clean up database session and flush any pending saves"""
        self._flush_pending_saves()
        if self._db_session:
            self._db_session.close()
            self._db_session = None
    
    def _extract_links(self, base_url: str, html: str, current_depth: int) -> List[str]:
        """
        Extract links from HTML content
        """
        links = []
        soup = BeautifulSoup(html, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            normalized = self._normalize_url(absolute_url)
            
            # Only follow links on same domain
            base_domain = self._extract_domain(base_url)
            link_domain = self._extract_domain(absolute_url)
            
            if base_domain == link_domain:
                links.append(normalized)
        
        return list(set(links))  # Remove duplicates
    
    def _scrape_page(self, url: str, depth: int = 0, visited: Optional[Set[str]] = None, 
                     scraped_urls: Optional[Set[str]] = None, log_callback: Optional[Callable] = None) -> List[PDFResult]:
        """
        Recursively scrape a page and follow links up to max_depth
        """
        if visited is None:
            visited = set()
        if scraped_urls is None:
            scraped_urls = set()
        
        results = []
        normalized_url = self._normalize_url(url)
        
        # Skip if already visited
        if normalized_url in visited:
            return results
        visited.add(normalized_url)
        
        # Skip duplicates if enabled
        if self.skip_duplicates and normalized_url in scraped_urls:
            if log_callback:
                log_callback(f"Skipping duplicate: {normalized_url}")
            return results
        
        try:
            if log_callback:
                log_callback(f"Scraping: {normalized_url} (depth {depth})")
            else:
                print(f"[MultiSiteScraper] Scraping: {normalized_url} (depth {depth})")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            print(f"[MultiSiteScraper] Successfully fetched: {normalized_url} (status: {response.status_code})")
            
            # Check if this is a direct PDF file
            if self._is_valid_extension(url):
                # Skip if from excluded site
                if self._is_excluded_site(url):
                    if log_callback:
                        log_callback(f"Skipping PDF from excluded site: {url}")
                    return results
                
                if self._matches_search_terms(url) and not self._matches_exclude_terms(url):
                    # Check file size if filters are set
                    file_size_mb = self._get_file_size_mb(url)
                    if file_size_mb:
                        if self.min_file_size_mb and file_size_mb < self.min_file_size_mb:
                            if log_callback:
                                log_callback(f"Skipping {url}: file size {file_size_mb:.2f}MB below minimum {self.min_file_size_mb}MB")
                            return results
                        if self.max_file_size_mb and file_size_mb > self.max_file_size_mb:
                            if log_callback:
                                log_callback(f"Skipping {url}: file size {file_size_mb:.2f}MB above maximum {self.max_file_size_mb}MB")
                            return results
                    
                    # Extract metadata from URL
                    metadata = self.extract_pdf_metadata(url, url.split('/')[-1])
                    
                    result = PDFResult(
                        url=normalized_url,
                        source_type='multi_site',
                        title=url.split('/')[-1],
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata=metadata
                    )
                    results.append(result)
                    scraped_urls.add(normalized_url)
                    
                    # Save to database immediately if enabled
                    if self.save_immediately:
                        self._save_pdf_to_database(result, log_callback)
                    elif log_callback:
                        log_callback(f"Found PDF: {normalized_url}")
                    
                    return results
            
            # Parse HTML for links and PDFs
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all PDF links on the page
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
            print(f"[MultiSiteScraper] Found {len(pdf_links)} PDF links on {normalized_url}")
            
            for link in pdf_links:
                pdf_url = urljoin(url, link['href'])
                pdf_url_normalized = self._normalize_url(pdf_url)
                
                # Skip if already scraped
                if pdf_url_normalized in scraped_urls:
                    continue
                
                # Skip if from excluded site
                if self._is_excluded_site(pdf_url):
                    if log_callback:
                        log_callback(f"Skipping PDF from excluded site: {pdf_url}")
                    continue
                
                # Get title from link text or URL (prefer link text)
                title = link.get_text(strip=True)
                if not title or title.strip() == '':
                    # Fallback to URL filename if link text is empty
                    title = pdf_url.split('/')[-1]
                    # If still empty, use a default title
                    if not title or title.strip() == '':
                        title = f"PDF from {urlparse(pdf_url).netloc}"
                title = title.strip()  # Ensure no leading/trailing whitespace
                
                # Check search and exclude terms
                if not self._matches_search_terms(pdf_url, title):
                    continue
                if self._matches_exclude_terms(pdf_url, title):
                    if log_callback:
                        log_callback(f"Excluding PDF based on terms: {pdf_url}")
                    continue
                
                # Check file size if filters are set
                file_size_mb = self._get_file_size_mb(pdf_url)
                if file_size_mb:
                    if self.min_file_size_mb and file_size_mb < self.min_file_size_mb:
                        continue
                    if self.max_file_size_mb and file_size_mb > self.max_file_size_mb:
                        continue
                
                # Extract metadata
                metadata = self.extract_pdf_metadata(pdf_url, title)
                
                result = PDFResult(
                    url=pdf_url_normalized,
                    source_type='multi_site',
                    title=title,
                    equipment_type=metadata.get('equipment_type'),
                    manufacturer=metadata.get('manufacturer'),
                    model=metadata.get('model'),
                    year=metadata.get('year'),
                    metadata=metadata
                )
                results.append(result)
                scraped_urls.add(pdf_url_normalized)
                
                # Save to database immediately if enabled
                if self.save_immediately:
                    self._save_pdf_to_database(result, log_callback)
                elif log_callback:
                    log_callback(f"Found PDF: {pdf_url_normalized}")
            
            # Check if this is a PDF directory (many PDFs on one page)
            if self.extract_directories and self._is_pdf_directory(url, response.text):
                if log_callback:
                    log_callback(f"Detected PDF directory: {normalized_url}")
            
            # Follow links if enabled and depth not exceeded
            if self.follow_links and depth < self.max_depth:
                links = self._extract_links(url, response.text, depth)
                
                for link in links[:20]:  # Limit links per page to avoid explosion
                    if link not in visited:
                        try:
                            sub_results = self._scrape_page(
                                link, depth + 1, visited, scraped_urls, log_callback
                            )
                            results.extend(sub_results)
                        except Exception as e:
                            if log_callback:
                                log_callback(f"Error following link {link}: {e}")
                            continue
            
        except requests.RequestException as e:
            error_msg = f"Error scraping {url}: {e}"
            if log_callback:
                log_callback(error_msg)
            print(f"[MultiSiteScraper] {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error scraping {url}: {e}"
            if log_callback:
                log_callback(error_msg)
            print(f"[MultiSiteScraper] {error_msg}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def search(self, query: str = None, log_callback: Optional[Callable] = None) -> List[PDFResult]:
        """
        Search across multiple sites for PDF files
        
        Args:
            query: Optional query string (can be used for search term matching or DuckDuckGo search)
            log_callback: Optional callback function for logging progress
            
        Returns:
            List of PDFResult objects
        """
        all_results = []
        visited_urls = set()
        scraped_urls = set()
        
        # If sites are provided as JSON string, parse them
        if isinstance(self.sites, str):
            try:
                self.sites = json.loads(self.sites)
            except json.JSONDecodeError:
                self.sites = []
        
        # If no sites provided, use DuckDuckGo to find sites based on search terms/query
        if not self.sites:
            # Build DuckDuckGo query from search terms or use the provided query
            ddg_query = query
            if self.search_terms:
                ddg_query = ' '.join(self.search_terms[:3])  # Use first 3 search terms
            
            if ddg_query:
                if log_callback:
                    log_callback(f"No sites provided, using DuckDuckGo to find sites for query: {ddg_query}")
                
                # Use DuckDuckGo to find sites containing PDFs
                ddg_config = {
                    'user_agent': self.config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
                    'request_timeout': self.config.get('timeout', 30),
                    'max_results': 20  # Get up to 20 results to find sites
                }
                
                ddg_scraper = DuckDuckGoScraper(ddg_config)
                
                if log_callback:
                    log_callback(f"Searching DuckDuckGo for: {ddg_query}")
                
                # Search DuckDuckGo to find sites
                ddg_results = ddg_scraper.search(ddg_query, max_results=20)
                
                if log_callback:
                    log_callback(f"DuckDuckGo returned {len(ddg_results)} results")
                
                # Extract unique domains from DuckDuckGo results
                domains_found = set()
                for result in ddg_results:
                    parsed_url = urlparse(result.url)
                    domain = parsed_url.netloc
                    domains_found.add(domain)
                
                # Convert domains to site URLs
                self.sites = [f"https://{domain}" for domain in domains_found]
                
                if log_callback:
                    log_callback(f"Found {len(self.sites)} sites from DuckDuckGo: {', '.join(list(self.sites)[:5])}...")
            else:
                if log_callback:
                    log_callback("No sites provided and no search terms/query available for DuckDuckGo search")
        
        if not self.sites:
            if log_callback:
                log_callback("No sites provided for scraping")
            return all_results
        
        if log_callback:
            log_callback(f"Starting multi-site scraping across {len(self.sites)} sites")
            log_callback(f"Search terms: {', '.join(self.search_terms) if self.search_terms else 'None'}")
            log_callback(f"Exclude terms: {', '.join(self.exclude_terms) if self.exclude_terms else 'None'}")
            log_callback(f"Exclude sites: {', '.join(self.exclude_sites) if self.exclude_sites else 'None'}")
            log_callback(f"Max depth: {self.max_depth}, Follow links: {self.follow_links}")
        
        try:
            # Scrape sites concurrently - increased workers for better performance
            max_workers = min(10, len(self.sites))  # Increased from 5 to 10
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_site = {
                    executor.submit(
                        self._scrape_site,
                        site,
                        visited_urls,
                        scraped_urls,
                        log_callback
                    ): site for site in self.sites
                }
                
                for future in as_completed(future_to_site):
                    site = future_to_site[future]
                    try:
                        results = future.result()
                        all_results.extend(results)
                        if log_callback:
                            log_callback(f"Completed scraping {site}: found {len(results)} PDFs")
                    except Exception as e:
                        error_msg = f"Error scraping {site}: {e}"
                        if log_callback:
                            log_callback(error_msg)
                        print(f"[MultiSiteScraper] {error_msg}")
                        import traceback
                        traceback.print_exc()
        finally:
            # Ensure all pending saves are flushed
            self._cleanup_db_session()
        
        if log_callback:
            log_callback(f"Multi-site scraping completed: found {len(all_results)} PDFs total")
        
        return all_results
    
    def _scrape_site(self, site_url: str, visited_urls: Set[str], scraped_urls: Set[str],
                     log_callback: Optional[Callable] = None) -> List[PDFResult]:
        """
        Scrape a single site
        """
        results = []
        
        try:
            # Ensure URL has a scheme
            if not site_url.startswith(('http://', 'https://')):
                site_url = f'https://{site_url}'
            
            # Check if this site is excluded
            if self._is_excluded_site(site_url):
                if log_callback:
                    log_callback(f"Skipping excluded site: {site_url}")
                return results
            
            results = self._scrape_page(site_url, 0, visited_urls, scraped_urls, log_callback)
            
        except Exception as e:
            error_msg = f"Error scraping site {site_url}: {e}"
            if log_callback:
                log_callback(error_msg)
            print(f"[MultiSiteScraper] {error_msg}")
            import traceback
            traceback.print_exc()
        finally:
            # Flush pending saves after each site to ensure data is saved
            if self._pending_saves:
                self._flush_pending_saves(log_callback)
        
        return results

"""
Google Drive link extractor for forum posts
"""
import re
import requests
from typing import List, Optional
from .base import BaseScraper, PDFResult


class GoogleDriveExtractor(BaseScraper):
    """Extractor for Google Drive links found in forum posts"""
    
    # Google Drive URL patterns
    DRIVE_PATTERNS = [
        r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
        r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
        r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)',
        r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)',
    ]
    
    def __init__(self, config: dict = None):
        super().__init__(config)
    
    def search(self, query: str) -> List[PDFResult]:
        """
        This is not a search method for GDrive, but rather an extractor.
        Use extract_from_page() instead.
        
        Args:
            query: Not used for GDrive extractor
            
        Returns:
            Empty list (use extract_from_page instead)
        """
        return []
    
    def extract_from_page(self, url: str, page_title: str = None) -> List[PDFResult]:
        """
        Extract Google Drive links from a page
        
        Args:
            url: URL of the page to extract links from
            page_title: Optional title of the page
            
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
            
            content = response.text
            
            # Find all Google Drive links
            for pattern in self.DRIVE_PATTERNS:
                matches = re.findall(pattern, content)
                
                for file_id in matches:
                    # Try to get direct download URL
                    direct_url = self._get_direct_download_url(file_id)
                    
                    if direct_url:
                        metadata = self.extract_pdf_metadata(direct_url, page_title)
                        
                        results.append(PDFResult(
                            url=direct_url,
                            source_type='gdrive',
                            source_url=url,
                            title=page_title or f"Google Drive File: {file_id}",
                            equipment_type=metadata.get('equipment_type'),
                            manufacturer=metadata.get('manufacturer'),
                            model=metadata.get('model'),
                            year=metadata.get('year'),
                            metadata={
                                **metadata,
                                'file_id': file_id,
                                'source_url': url
                            }
                        ))
        
        except requests.RequestException as e:
            print(f"Error fetching page {url}: {e}")
        except Exception as e:
            print(f"Error extracting GDrive links from {url}: {e}")
        
        return results
    
    def extract_from_text(self, text: str, page_title: str = None) -> List[PDFResult]:
        """
        Extract Google Drive links from text content
        
        Args:
            text: Text content to search for GDrive links
            page_title: Optional title of the source
            
        Returns:
            List of PDFResult objects
        """
        results = []
        
        # Find all Google Drive links
        for pattern in self.DRIVE_PATTERNS:
            matches = re.findall(pattern, text)
            
            for file_id in matches:
                # Try to get direct download URL
                direct_url = self._get_direct_download_url(file_id)
                
                if direct_url:
                    metadata = self.extract_pdf_metadata(direct_url, page_title)
                    
                    results.append(PDFResult(
                        url=direct_url,
                        source_type='gdrive',
                        title=page_title or f"Google Drive File: {file_id}",
                        equipment_type=metadata.get('equipment_type'),
                        manufacturer=metadata.get('manufacturer'),
                        model=metadata.get('model'),
                        year=metadata.get('year'),
                        metadata={
                            **metadata,
                            'file_id': file_id
                        }
                    ))
        
        return results
    
    def _get_direct_download_url(self, file_id: str) -> Optional[str]:
        """
        Get direct download URL for a Google Drive file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Direct download URL or None if not a PDF
        """
        try:
            # Try to get file info
            info_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            response = requests.head(
                info_url,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent},
                allow_redirects=False
            )
            
            # Check if it's a PDF by looking at the content type
            content_type = response.headers.get('Content-Type', '')
            
            if 'pdf' in content_type.lower():
                # Return direct download URL
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            
            # If we can't determine content type, still return the download URL
            # The PDF downloader will validate it
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        
        except Exception as e:
            print(f"Error getting direct download URL for {file_id}: {e}")
            return None
    
    def is_gdrive_url(self, url: str) -> bool:
        """
        Check if URL is a Google Drive URL
        
        Args:
            url: URL to check
            
        Returns:
            True if it's a Google Drive URL
        """
        return any(pattern in url for pattern in ['drive.google.com', 'docs.google.com'])

"""
PDF download handler with approval workflow
"""
import os
import hashlib
import requests
from pathlib import Path
from typing import Optional
from app.config import get_settings
from app.utils import generate_safe_filename

settings = get_settings()


class PDFDownloader:
    """Handle PDF downloads with validation"""
    
    def __init__(self):
        self.download_dir = Path(settings.database_path).parent / 'pdfs'
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = settings.max_pdf_size_mb
        self.timeout = settings.request_timeout
    
    def download(
        self,
        url: str,
        manual_id: int = None,
        manufacturer: str = None,
        model: str = None,
        year: str = None
    ) -> Optional[str]:
        """
        Download PDF from URL
        
        Args:
            url: URL to download from
            manual_id: Optional manual ID for filename
            manufacturer: Manufacturer name for meaningful filename
            model: Model name for meaningful filename
            year: Year for meaningful filename
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Validate URL
            if not self._is_valid_pdf_url(url):
                print(f"Invalid PDF URL: {url}")
                return None
            
            # Download with streaming
            response = requests.get(
                url,
                stream=True,
                timeout=self.timeout,
                headers={'User-Agent': settings.user_agent}
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                print(f"Invalid content type: {content_type}")
                return None
            
            # Check content length
            content_length = int(response.headers.get('Content-Length', 0))
            max_size_bytes = self.max_size_mb * 1024 * 1024
            
            if content_length > max_size_bytes:
                print(f"File too large: {content_length} bytes (max: {max_size_bytes})")
                return None
            
            # Generate filename
            filename = self._generate_filename(url, manual_id, manufacturer, model, year)
            filepath = self.download_dir / filename
            
            # Download file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Validate downloaded file
            if self._validate_pdf(filepath):
                return str(filepath)
            else:
                # Remove invalid file
                filepath.unlink()
                return None
        
        except requests.RequestException as e:
            print(f"Download error: {e}")
            return None
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None
    
    def _is_valid_pdf_url(self, url: str) -> bool:
        """Check if URL is valid for PDF download"""
        url_lower = url.lower()
        return (
            url_lower.endswith('.pdf') or
            'filetype:pdf' in url_lower or
            'drive.google.com' in url_lower or
            'docs.google.com' in url_lower
        )
    
    def _generate_filename(
        self,
        url: str,
        manual_id: int = None,
        manufacturer: str = None,
        model: str = None,
        year: str = None
    ) -> str:
        """Generate unique filename for PDF"""
        import re
        
        # Try to extract model/year from URL if not provided
        if not model or not year:
            # Extract from URL path
            url_parts = url.split('/')
            for part in url_parts:
                # Look for year (4 digits starting with 19 or 20)
                year_match = re.search(r'\b(19|20)\d{2}\b', part)
                if year_match and not year:
                    year = year_match.group()
                # Look for model patterns (letters followed by numbers)
                if re.match(r'^[a-z]{2,}\d+', part.lower()) and not model:
                    model = part.upper()
        
        # Try to generate meaningful filename from metadata
        if manufacturer or model or year:
            safe_name = generate_safe_filename(manufacturer, model, year)
            # Use the generated name as long as it has more than just manufacturer
            if safe_name and safe_name != "manual":
                return safe_name + ".pdf"
        
        # Fallback to hash-based filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        
        if manual_id:
            return f"manual_{manual_id}_{url_hash}.pdf"
        else:
            return f"manual_{url_hash}.pdf"
    
    def _validate_pdf(self, filepath: Path) -> bool:
        """Validate that file is a valid PDF"""
        try:
            # Check file exists and has content
            if not filepath.exists() or filepath.stat().st_size == 0:
                return False
            
            # Check PDF header
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False
            
            return True
        except Exception as e:
            print(f"Error validating PDF: {e}")
            return False
    
    def get_file_size(self, filepath: str) -> int:
        """Get file size in bytes"""
        path = Path(filepath)
        if path.exists():
            return path.stat().st_size
        return 0
    
    def delete_file(self, filepath: str) -> bool:
        """Delete downloaded PDF file"""
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

"""
PDF processing module for extracting text and generating images
"""
import os
from pathlib import Path
from typing import List, Optional, Dict
import PyPDF2
import pdfplumber
from PIL import Image
import io
from app.config import get_settings
from app.utils import generate_safe_filename

settings = get_settings()


class PDFProcessor:
    """Process PDF files to extract text and generate images"""
    
    def __init__(self):
        self.image_dir = Path(settings.database_path).parent / 'images'
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.image_dpi = settings.image_dpi
        self.image_format = settings.image_format.lower()
        self.main_image_page = settings.main_image_page
        self.additional_image_pages = settings.additional_image_pages_list
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """
        Extract metadata from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with metadata
        """
        import re
        from app.utils import extract_model_year_from_title, parse_make_model_modelnumber
        
        metadata = {
            'title': None,
            'author': None,
            'subject': None,
            'keywords': None,
            'creator': None,
            'producer': None,
            'page_count': 0,
            'manufacturer': None,
            'model': None,
            'year': None
        }
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                
                # Get document info
                info = pdf.metadata
                if info:
                    title = info.get('/Title')
                    metadata['title'] = title
                    
                    # Extract manufacturer, model and year from title
                    if title:
                        parsed = parse_make_model_modelnumber(title)
                        if parsed.get('make'):
                            metadata['manufacturer'] = parsed['make']
                        if parsed.get('model'):
                            metadata['model'] = parsed['model']
                        
                        model, year = extract_model_year_from_title(title)
                        if model and not metadata['model']:
                            metadata['model'] = model
                        if year:
                            metadata['year'] = year
                    
                    metadata['author'] = info.get('/Author')
                    metadata['subject'] = info.get('/Subject')
                    metadata['keywords'] = info.get('/Keywords')
                    metadata['creator'] = info.get('/Creator')
                    metadata['producer'] = info.get('/Producer')
                
                # Get page count
                metadata['page_count'] = len(pdf.pages)
        
        except Exception as e:
            print(f"Error extracting PDF metadata: {e}")
        
        return metadata
    
    def extract_metadata_from_filename(self, filename: str) -> Dict:
        """
        Extract metadata from a filename
        
        Args:
            filename: PDF filename
            
        Returns:
            Dictionary with metadata
        """
        from app.utils import parse_make_model_modelnumber, extract_model_year_from_title
        
        # Remove .pdf extension
        title = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
        
        # Parse make, model, model number
        parsed = parse_make_model_modelnumber(title)
        
        # Extract year
        year_match = None
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        year = year_match.group() if year_match else None
        
        metadata = {
            'title': title,
            'manufacturer': parsed.get('make'),
            'model': parsed.get('model'),
            'year': year,
            'equipment_type': None
        }
        
        return metadata
    
    def extract_text(self, pdf_path: str, max_pages: int = 5) -> str:
        """
        Extract text from PDF
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to extract text from
            
        Returns:
            Extracted text
        """
        text = ""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages[:max_pages]):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {i + 1} ---\n"
                        text += page_text + "\n"
        
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
        
        return text
    
    def extract_first_page_text(self, pdf_path: str) -> str:
        """
        Extract text from first page only
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Text from first page
        """
        return self.extract_text(pdf_path, max_pages=1)
    
    def find_index_page(self, pdf_path: str) -> Optional[int]:
        """
        Find the index/table of contents page
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Page number (1-indexed) or None
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check first 10 pages for index
                for i, page in enumerate(pdf.pages[:10]):
                    text = page.extract_text()
                    if text:
                        text_lower = text.lower()
                        # Look for index indicators
                        index_keywords = ['table of contents', 'contents', 'index', 'toc']
                        if any(keyword in text_lower for keyword in index_keywords):
                            return i + 1  # Return 1-indexed page number
        
        except Exception as e:
            print(f"Error finding index page: {e}")
        
        return None
    
    def convert_page_to_image(
        self,
        pdf_path: str,
        page_num: int,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert a PDF page to an image
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            output_path: Optional output path
            
        Returns:
            Path to generated image or None
        """
        try:
            # Generate output path if not provided
            if output_path is None:
                pdf_name = Path(pdf_path).stem
                output_path = str(
                    self.image_dir / f"{pdf_name}_page{page_num}.{self.image_format}"
                )
            
            # Use pdfplumber to render page as image
            with pdfplumber.open(pdf_path) as pdf:
                if page_num < 1 or page_num > len(pdf.pages):
                    return None
                
                page = pdf.pages[page_num - 1]
                
                # Convert to image
                img = page.to_image(resolution=self.image_dpi)
                
                # Convert PIL Image to RGB if needed (JPEG doesn't support palette mode)
                if hasattr(img, 'original'):
                    pil_img = img.original
                else:
                    pil_img = img
                
                # Convert to RGB mode if necessary
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                
                # Save the image
                pil_img.save(output_path, format=self.image_format.upper())
                
                return output_path
        
        except Exception as e:
            print(f"Error converting page {page_num} to image: {e}")
            return None
    
    def _generate_safe_filename(self, manufacturer: str, model: str, model_number: str = None, year: str = None) -> str:
        """
        Generate a safe filename from manual metadata
        
        Args:
            manufacturer: Manufacturer name
            model: Model name
            model_number: Model number
            year: Year
            
        Returns:
            Safe filename string
        """
        return generate_safe_filename(manufacturer, model, model_number, year)
    
    def generate_listing_images(
        self,
        pdf_path: str,
        manual_id: int,
        manufacturer: str = None,
        model: str = None,
        model_number: str = None,
        year: str = None
    ) -> Dict[str, List[str]]:
        """
        Generate images for Etsy listing
        
        Args:
            pdf_path: Path to PDF file
            manual_id: Manual ID for naming
            manufacturer: Manufacturer name
            model: Model name
            model_number: Model number
            year: Year
            
        Returns:
            Dictionary with 'main' and 'additional' image paths
        """
        images = {
            'main': [],
            'additional': []
        }
        
        try:
            # Extract PDF metadata to get model/year if not provided
            if not model or not year:
                pdf_metadata = self.extract_metadata(pdf_path)
                if not model and pdf_metadata.get('model'):
                    model = pdf_metadata.get('model')
                if not year and pdf_metadata.get('year'):
                    year = pdf_metadata.get('year')
            
            # Also try to extract from PDF filename (which comes from URL)
            import re
            if not model or not year:
                pdf_filename = Path(pdf_path).stem
                # Extract year from filename
                year_match = re.search(r'\b(19|20)\d{2}\b', pdf_filename)
                if year_match and not year:
                    year = year_match.group()
                # Extract model from filename (letters followed by numbers)
                model_match = re.search(r'[A-Z]{2,}\d+', pdf_filename)
                if model_match and not model:
                    model = model_match.group()
            
            # Extract model_number from model if it's not provided
            if not model_number and model:
                # Try to extract numeric part from model
                number_match = re.search(r'\d+', model)
                if number_match:
                    model_number = number_match.group()
            
            # Generate meaningful filename
            pdf_name = self._generate_safe_filename(manufacturer, model, model_number, year)
             
            # Generate main image (first page)
            main_image_path = self.convert_page_to_image(
                pdf_path,
                self.main_image_page,
                str(self.image_dir / f"{pdf_name}_main.{self.image_format}")
            )
            
            # Only generate if doesn't exist
            if main_image_path and not os.path.exists(main_image_path):
                images['main'].append(main_image_path)
            elif main_image_path:
                # Image already exists, reuse it
                images['main'].append(main_image_path)
            
            # Find index page
            index_page = self.find_index_page(pdf_path)
            
            # Generate additional images
            pages_to_convert = []
            
            # Get total page count
            total_pages = self.get_page_count(pdf_path)
            
            # Add index page if found
            if index_page and index_page != self.main_image_page:
                pages_to_convert.append(index_page)
            
            # Add configured additional pages
            for page in self.additional_image_pages:
                if page != self.main_image_page and page not in pages_to_convert:
                    pages_to_convert.append(page)
            
            # If we don't have enough pages yet, add evenly distributed pages
            # We want at least 5 images total (1 main + 4 additional)
            needed_additional = 5 - len(pages_to_convert)
            if needed_additional > 0:
                # Calculate evenly distributed pages
                step = max(2, total_pages // (needed_additional + 1))
                for i in range(needed_additional):
                    next_page = ((i + 1) * step) + self.main_image_page
                    if next_page <= total_pages and next_page not in pages_to_convert:
                        pages_to_convert.append(next_page)
            
            # Convert pages (up to 4 additional)
            for i, page_num in enumerate(pages_to_convert[:4]):  # Max 4 additional images
                image_path = self.convert_page_to_image(
                    pdf_path,
                    page_num,
                    str(self.image_dir / f"{pdf_name}_additional_{i}.{self.image_format}")
                )
                
                # Only generate if doesn't exist
                if image_path and not os.path.exists(image_path):
                    images['additional'].append(image_path)
                elif image_path:
                    # Image already exists, reuse it
                    images['additional'].append(image_path)
        
        except Exception as e:
            print(f"Error generating listing images: {e}")
            print(f"PDF Path: {pdf_path}")
            print(f"Manual ID: {manual_id}")
            print(f"Image Dir: {self.image_dir}")
            print(f"Image Dir exists: {self.image_dir.exists()}")
        
        return images
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        Get total page count of PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Number of pages
        """
        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                return len(pdf.pages)
        except Exception as e:
            print(f"Error getting page count: {e}")
            return 0
    
    def cleanup_images(
        self,
        manual_id: int = None,
        manufacturer: str = None,
        model: str = None,
        model_number: str = None,
        year: str = None
    ) -> bool:
        """
        Clean up generated images for a manual
        
        Args:
            manual_id: Manual ID (for backward compatibility)
            manufacturer: Manufacturer name
            model: Model name
            model_number: Model number
            year: Year
            
        Returns:
            True if successful
        """
        try:
            # Try to use meaningful filename if metadata is provided
            if manufacturer or model or year:
                pdf_name = self._generate_safe_filename(manufacturer, model, model_number, year)
            else:
                # Fallback to old naming scheme
                pdf_name = f"manual_{manual_id}"
             
            # Remove main image
            main_image = self.image_dir / f"{pdf_name}_main.{self.image_format}"
            if main_image.exists():
                main_image.unlink()
             
            # Remove additional images
            for i in range(10):  # Check up to 10 additional images
                additional_image = self.image_dir / f"{pdf_name}_additional_{i}.{self.image_format}"
                if additional_image.exists():
                    additional_image.unlink()
             
            return True
        
        except Exception as e:
            print(f"Error cleaning up images: {e}")
            return False

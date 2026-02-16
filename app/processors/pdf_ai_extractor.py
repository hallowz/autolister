"""
AI-based PDF metadata extractor using free Groq API
Extracts manufacturer, model, year, and title from PDF pages
"""
import os
import base64
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple
from app.config import get_settings

settings = get_settings()


class PDFAIExtractor:
    """Extract metadata from PDF using AI analysis"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AI extractor
        
        Args:
            api_key: Groq API key (defaults to environment variable GROQ_API_KEY)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"  # Free tier model
        self.timeout = 30
    
    def extract_from_pdf(
        self,
        pdf_path: str,
        max_pages: int = 3,
        max_chars_per_page: int = 3000
    ) -> Dict[str, Optional[str]]:
        """
        Extract metadata from PDF file
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to analyze (first pages typically have title info)
            max_chars_per_page: Maximum characters to extract per page
            
        Returns:
            Dictionary with extracted metadata:
            - manufacturer: Manufacturer name
            - model: Model name
            - year: Year (4 digits)
            - title: Full title
            - success: Whether extraction succeeded
            - error: Error message if failed
        """
        result = {
            'manufacturer': None,
            'model': None,
            'year': None,
            'title': None,
            'success': False,
            'error': None
        }
        
        # Check if API key is available
        if not self.api_key:
            result['error'] = 'GROQ_API_KEY not configured'
            return result
        
        # Check if PDF exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            result['error'] = f'PDF file not found: {pdf_path}'
            return result
        
        try:
            # Extract text from first few pages
            text_content = self._extract_pdf_text(pdf_path, max_pages, max_chars_per_page)
            
            if not text_content or len(text_content.strip()) < 50:
                result['error'] = 'Could not extract sufficient text from PDF'
                return result
            
            # Use AI to extract metadata
            extracted = self._extract_metadata_with_ai(text_content)
            
            if extracted:
                result.update(extracted)
                result['success'] = True
            else:
                result['error'] = 'AI extraction returned no results'
        
        except Exception as e:
            result['error'] = f'Extraction error: {str(e)}'
        
        return result
    
    def _extract_pdf_text(
        self,
        pdf_path: str,
        max_pages: int,
        max_chars_per_page: int
    ) -> str:
        """
        Extract text from PDF pages
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to extract
            max_chars_per_page: Max characters per page
            
        Returns:
            Combined text from pages
        """
        try:
            import PyPDF2
            
            text_parts = []
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Limit to available pages
                num_pages = min(len(reader.pages), max_pages)
                
                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    
                    if text:
                        # Clean up text and limit length
                        text = text.strip()
                        if len(text) > max_chars_per_page:
                            text = text[:max_chars_per_page]
                        
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            
            return "\n\n".join(text_parts)
        
        except ImportError:
            # Fallback: try using pdfplumber if PyPDF2 not available
            try:
                import pdfplumber
                
                text_parts = []
                
                with pdfplumber.open(pdf_path) as pdf:
                    num_pages = min(len(pdf.pages), max_pages)
                    
                    for page_num in range(num_pages):
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        
                        if text:
                            text = text.strip()
                            if len(text) > max_chars_per_page:
                                text = text[:max_chars_per_page]
                            
                            text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                
                return "\n\n".join(text_parts)
            
            except ImportError:
                raise Exception("Neither PyPDF2 nor pdfplumber is installed. Install with: pip install PyPDF2")
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def _extract_metadata_with_ai(self, text: str) -> Optional[Dict[str, Optional[str]]]:
        """
        Use AI to extract metadata from PDF text
        
        Args:
            text: Text extracted from PDF
            
        Returns:
            Dictionary with extracted metadata or None if failed
        """
        # Prepare the prompt
        prompt = f"""You are analyzing a product manual PDF. Extract the following information from the text below:

1. Manufacturer (brand/company name)
2. Model name or model number
3. Year (if mentioned, 4-digit year)
4. Full title of the manual

PDF Text:
{text[:8000]}

Return ONLY a valid JSON object with these exact keys:
- manufacturer: string or null
- model: string or null  
- year: string (4 digits) or null
- title: string or null

If you cannot find a piece of information, use null. Do not include any explanations or text outside the JSON."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts structured data from product manuals. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # Low temperature for consistent extraction
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Parse JSON result
            extracted = json.loads(content)
            
            # Validate and clean the result
            result = {
                'manufacturer': self._clean_string(extracted.get('manufacturer')),
                'model': self._clean_string(extracted.get('model')),
                'year': self._clean_year(extracted.get('year')),
                'title': self._clean_string(extracted.get('title'))
            }
            
            return result
        
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            return None
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during AI extraction: {e}")
            return None
    
    def _clean_string(self, value: Optional[str]) -> Optional[str]:
        """Clean and validate string value"""
        if value is None:
            return None
        
        value = str(value).strip()
        
        # Remove common artifacts
        value = value.strip('"\'').strip()
        
        # Return None if empty or just placeholder text
        if not value or value.lower() in ['null', 'none', 'n/a', 'unknown']:
            return None
        
        return value
    
    def _clean_year(self, value: Optional[str]) -> Optional[str]:
        """Clean and validate year value"""
        if value is None:
            return None
        
        value = str(value).strip()
        
        # Extract 4-digit year if present
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', value)
        
        if year_match:
            return year_match.group()
        
        return None
    
    def is_available(self) -> bool:
        """Check if the AI extractor is available (API key configured)"""
        return bool(self.api_key)


# Convenience function for quick extraction
def extract_pdf_metadata(pdf_path: str) -> Dict[str, Optional[str]]:
    """
    Convenience function to extract metadata from a PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with extracted metadata
    """
    extractor = PDFAIExtractor()
    return extractor.extract_from_pdf(pdf_path)

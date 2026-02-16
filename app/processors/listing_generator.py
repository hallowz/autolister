"""
AI-based listing content generator for Etsy listings
Generates SEO-optimized titles, detailed descriptions, and tags from PDF content
"""
import os
import json
import requests
from pathlib import Path
from typing import Optional, Dict, List
from app.config import get_settings

settings = get_settings()


class ListingContentGenerator:
    """Generate listing content (title, description, tags) using AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the listing content generator
        
        Args:
            api_key: Groq API key (defaults to environment variable GROQ_API_KEY)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
        self.timeout = 30
    
    def generate_all_content(
        self,
        pdf_path: str,
        metadata: Dict,
        max_pages: int = 10,
        max_chars_per_page: int = 5000
    ) -> Dict:
        """
        Generate all listing content (title, description, tags) from PDF
        
        Args:
            pdf_path: Path to PDF file
            metadata: Dictionary with manufacturer, model, year, title, page_count
            max_pages: Maximum number of pages to analyze
            max_chars_per_page: Maximum characters to extract per page
            
        Returns:
            Dictionary with:
            - seo_title: SEO-optimized title
            - description: Detailed description
            - tags: List of tags
            - success: Whether generation succeeded
            - error: Error message if failed
        """
        result = {
            'seo_title': None,
            'description': None,
            'tags': None,
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
            # Extract text from PDF
            text_content = self._extract_pdf_text(pdf_path, max_pages, max_chars_per_page)
            
            if not text_content or len(text_content.strip()) < 100:
                result['error'] = 'Could not extract sufficient text from PDF'
                return result
            
            # Generate all content
            seo_title = self._generate_seo_title(text_content, metadata)
            description = self._generate_description(text_content, metadata)
            tags = self._generate_tags(text_content, metadata)
            
            if seo_title and description and tags:
                result['seo_title'] = seo_title
                result['description'] = description
                result['tags'] = tags
                result['success'] = True
            else:
                result['error'] = 'AI content generation returned incomplete results'
        
        except Exception as e:
            result['error'] = f'Generation error: {str(e)}'
        
        return result
    
    def _extract_pdf_text(
        self,
        pdf_path: str,
        max_pages: int,
        max_chars_per_page: int
    ) -> str:
        """Extract text from PDF pages"""
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
                raise Exception("Neither PyPDF2 nor pdfplumber is installed")
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def _generate_seo_title(self, text: str, metadata: Dict) -> Optional[str]:
        """
        Generate SEO-optimized title
        
        Format example: "Honda Pioneer SXS700 M2/M4 Service Manual | 2014–2024 UTV Repair Guide | Instant Digital Download | PDF"
        """
        manufacturer = metadata.get('manufacturer', 'Unknown')
        model = metadata.get('model', 'Unknown')
        year = metadata.get('year', '')
        title = metadata.get('title', 'Service Manual')
        page_count = metadata.get('page_count', '')
        
        prompt = f"""You are creating an SEO-optimized Etsy listing title for a digital service manual.

Product Information:
- Manufacturer: {manufacturer}
- Model: {model}
- Year: {year if year else 'Not specified'}
- Title: {title}
- Page Count: {page_count if page_count else 'Unknown'}

PDF Content (first pages):
{text[:5000]}

Create a compelling, SEO-optimized title following this EXACT format:
"[Manufacturer] [Model] Service Manual | [Year Range] [Vehicle Type] Repair Guide | Instant Digital Download | PDF"

Rules:
1. Use pipe symbols (|) to separate sections
2. Include the manufacturer and model at the start
3. Include year range if multiple years are mentioned, otherwise single year
4. Include vehicle type (UTV, ATV, Motorcycle, Car, Truck, etc.)
5. End with "Instant Digital Download | PDF"
6. Keep it under 140 characters if possible
7. Make it keyword-rich for Etsy search
8. If year is not specified, use "All Years" or omit the year section

Return ONLY the title text, no explanations or extra formatting."""
        
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
                        "content": "You are an SEO expert specializing in Etsy product titles. Create keyword-rich, compelling titles."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 200
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            data = response.json()
            title = data['choices'][0]['message']['content'].strip()
            
            # Clean up
            title = title.strip('"\'').strip()
            
            return title
        
        except Exception as e:
            print(f"Error generating SEO title: {e}")
            return None
    
    def _generate_description(self, text: str, metadata: Dict) -> Optional[str]:
        """
        Generate detailed description following the Etsy listing format
        """
        manufacturer = metadata.get('manufacturer', 'Unknown')
        model = metadata.get('model', 'Unknown')
        year = metadata.get('year', '')
        title = metadata.get('title', 'Service Manual')
        page_count = metadata.get('page_count', '')
        
        prompt = f"""You are creating a professional Etsy listing description for a digital service manual.

Product Information:
- Manufacturer: {manufacturer}
- Model: {model}
- Year: {year if year else 'Not specified'}
- Title: {title}
- Page Count: {page_count if page_count else 'Unknown'}

PDF Content (first pages):
{text[:12000]}

Create a comprehensive, professional description following this EXACT structure:

[Year] [Manufacturer] [Model] SERVICE MANUAL
• [Manufacturer] original service manual
• Adobe Acrobat (PDF) format
• Fully Searchable
• Easily print any or all content
• Provided via direct download shortly after purchase
• Everything needed to repair & maintain your motor
• Troubleshooting instructions, diagrams and reference material.

MODELS COVERED:
• [List all model variants mentioned in the PDF]
• All Models [Year range or years mentioned]

TABLE OF CONTENTS ([Page Count] Pages)
[Extract and list the main sections from the table of contents]
1. [First section]
2. [Second section]
[Continue listing major sections...]

WHAT'S INCLUDED:
• Complete engine disassembly and assembly procedures
• Fuel and system diagnostics and repair
• Electrical, ignition, and charging system procedures
• Cooling system inspection and maintenance
• Clutch, drivetrain, and transmission service
• Suspension, chassis, and steering procedures
• Control linkage adjustments
• Troubleshooting charts and diagnostic workflows
• OEM specifications and torque tables
• High-resolution wiring and system diagrams

FEATURES:
• OEM-quality PDF (searchable and printable)
• High-resolution diagrams and schematics
• Instant digital download after purchase
• Works on PC, Mac, tablet, and mobile devices

IMPORTANT:
This is a digital PDF manual. No physical book will be shipped.

DON'T SEE WHAT YOU NEED?
We have many other manuals available on Etsy and an even larger offline library.
Send a message with your brand, model, and year and we'll direct you to the correct listing or check our library and list what you need.

Rules:
1. Use bullet points (•) for lists
2. Keep the formatting exactly as shown
3. Extract real information from the PDF content
4. If year is not specified, use the title or omit
5. If models covered is not clear, use the main model
6. Extract actual table of contents from the PDF
7. Make it professional and accurate
8. Return ONLY the description text, no explanations

Return ONLY the description text, no explanations or extra formatting."""
        
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
                        "content": "You are a professional copywriter specializing in digital product listings for Etsy. Create accurate, detailed descriptions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 2000
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            data = response.json()
            description = data['choices'][0]['message']['content'].strip()
            
            # Clean up
            description = description.replace('```', '').strip()
            
            return description
        
        except Exception as e:
            print(f"Error generating description: {e}")
            return None
    
    def _generate_tags(self, text: str, metadata: Dict) -> Optional[List[str]]:
        """
        Generate relevant Etsy tags
        """
        manufacturer = metadata.get('manufacturer', 'Unknown')
        model = metadata.get('model', 'Unknown')
        year = metadata.get('year', '')
        title = metadata.get('title', 'Service Manual')
        
        prompt = f"""You are creating Etsy tags for a digital service manual listing.

Product Information:
- Manufacturer: {manufacturer}
- Model: {model}
- Year: {year if year else 'Not specified'}
- Title: {title}

PDF Content (first pages):
{text[:5000]}

Generate 13 relevant Etsy tags following these rules:
1. Tags should be 1-3 words each
2. Include manufacturer name
3. Include model name/number
4. Include year if specified
5. Include relevant keywords like: Service Manual, Repair Guide, PDF, Digital Download, OEM, Workshop Manual
6. Include vehicle type (UTV, ATV, Motorcycle, Car, Truck, etc.)
7. Make them keyword-rich for Etsy search
8. Each tag should be 20 characters or less when possible

Return ONLY a valid JSON array of strings, no explanations or extra formatting.
Example: ["Honda", "Pioneer 700", "Service Manual", "UTV", "Repair Guide", "PDF", "Digital Download", "OEM", "Workshop Manual", "2014", "SXS700", "Manual", "Honda Pioneer"]"""
        
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
                        "content": "You are an Etsy SEO expert. Generate relevant, searchable tags for product listings."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 300,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Parse JSON result
            result = json.loads(content)
            
            # Extract tags array
            tags = result.get('tags', [])
            
            if not tags:
                # Try parsing as direct array
                try:
                    tags = json.loads(content)
                except:
                    pass
            
            # Ensure we have exactly 13 tags
            if len(tags) > 13:
                tags = tags[:13]
            elif len(tags) < 13:
                # Add default tags if needed
                default_tags = ["Service Manual", "Repair Guide", "PDF", "Digital Download"]
                for tag in default_tags:
                    if tag not in tags and len(tags) < 13:
                        tags.append(tag)
            
            return tags
        
        except Exception as e:
            print(f"Error generating tags: {e}")
            # Return default tags
            return [
                manufacturer,
                model,
                "Service Manual",
                "Repair Guide",
                "PDF",
                "Digital Download",
                "OEM",
                "Workshop Manual",
                "Manual",
                "Repair",
                "Maintenance",
                "DIY",
                "Instant Download"
            ]
    
    def generate_listing_data_file(
        self,
        pdf_path: str,
        metadata: Dict,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a unified listing data file with all content
        
        Args:
            pdf_path: Path to PDF file
            metadata: Dictionary with manufacturer, model, year, title, page_count
            output_path: Path to save the listing data file (optional)
            
        Returns:
            Path to the generated file or None if failed
        """
        # Generate all content
        content = self.generate_all_content(pdf_path, metadata)
        
        if not content['success']:
            print(f"Failed to generate listing content: {content['error']}")
            return None
        
        # Determine output path
        if not output_path:
            pdf_file = Path(pdf_path)
            output_path = str(pdf_file.parent / f"{pdf_file.stem}_listing_data.json")
        
        # Prepare the listing data
        listing_data = {
            'manufacturer': metadata.get('manufacturer'),
            'model': metadata.get('model'),
            'year': metadata.get('year'),
            'title': metadata.get('title'),
            'page_count': metadata.get('page_count'),
            'seo_title': content['seo_title'],
            'description': content['description'],
            'tags': content['tags'],
            'generated_at': None  # Will be set when saved
        }
        
        try:
            from datetime import datetime
            listing_data['generated_at'] = datetime.utcnow().isoformat() + 'Z'
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(listing_data, f, indent=2, ensure_ascii=False)
            
            return output_path
        
        except Exception as e:
            print(f"Error writing listing data file: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if the generator is available (API key configured)"""
        return bool(self.api_key)


# Convenience function
def generate_listing_content(pdf_path: str, metadata: Dict) -> Dict:
    """
    Convenience function to generate all listing content
    
    Args:
        pdf_path: Path to PDF file
        metadata: Dictionary with manufacturer, model, year, title, page_count
        
    Returns:
        Dictionary with seo_title, description, tags, success, error
    """
    generator = ListingContentGenerator()
    return generator.generate_all_content(pdf_path, metadata)

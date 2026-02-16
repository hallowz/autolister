"""
Summary generator for creating Etsy listing titles and descriptions
"""
import re
from typing import Dict, Optional
from app.config import get_settings

settings = get_settings()


class SummaryGenerator:
    """Generate listing titles and descriptions from PDF content"""
    
    def __init__(self):
        self.default_price = settings.etsy_default_price
    
    def generate_title(
        self,
        metadata: Dict,
        extracted_text: str = None
    ) -> str:
        """
        Generate listing title from metadata and extracted text
        
        Args:
            metadata: PDF metadata dictionary
            extracted_text: Optional extracted text from PDF
            
        Returns:
            Listing title
        """
        parts = []
        
        # Add manufacturer if available
        manufacturer = metadata.get('manufacturer')
        if manufacturer:
            parts.append(manufacturer)
        
        # Add model if available
        model = metadata.get('model')
        if model:
            parts.append(model)
        
        # Add year if available
        year = metadata.get('year')
        if year:
            parts.append(year)
        
        # Add equipment type if available
        equipment_type = metadata.get('equipment_type')
        if equipment_type:
            parts.append(equipment_type)
        
        # Add PDF title if available
        pdf_title = metadata.get('title')
        if pdf_title and len(pdf_title) < 100:
            parts.append(pdf_title)
        
        # If we don't have enough parts, try to extract from text
        if len(parts) < 2 and extracted_text:
            extracted_parts = self._extract_from_text(extracted_text)
            parts.extend(extracted_parts)
        
        # Always add "Service Manual" or "Owner's Manual"
        if not any('manual' in part.lower() for part in parts):
            parts.append("Service Manual")
        
        # Join parts
        title = " ".join(parts)
        
        # Clean up title
        title = self._clean_title(title)
        
        # Ensure title isn't too long (Etsy limit is 140 characters)
        if len(title) > 140:
            title = title[:137] + "..."
        
        return title
    
    def generate_description(
        self,
        metadata: Dict,
        extracted_text: str = None,
        page_count: int = 0
    ) -> str:
        """
        Generate listing description from metadata and extracted text
        
        Args:
            metadata: PDF metadata dictionary
            extracted_text: Optional extracted text from PDF
            page_count: Number of pages in PDF
            
        Returns:
            Listing description
        """
        description_parts = []
        
        # Add title
        title = self.generate_title(metadata, extracted_text)
        description_parts.append(f"📖 {title}\n")
        
        # Add comprehensive details section
        description_parts.append("\n📋 Manual Details:\n")
        
        if metadata.get('manufacturer'):
            description_parts.append(f"• Manufacturer: {metadata['manufacturer']}\n")
        
        if metadata.get('model'):
            description_parts.append(f"• Model: {metadata['model']}\n")
        
        if metadata.get('year'):
            description_parts.append(f"• Year: {metadata['year']}\n")
        
        if page_count > 0:
            description_parts.append(f"• Pages: {page_count}\n")
        
        if metadata.get('equipment_type'):
            description_parts.append(f"• Type: {metadata['equipment_type']}\n")
        
        # Add format info
        description_parts.append("\n📄 Format:\n")
        description_parts.append("• Digital PDF Download\n")
        description_parts.append("• High Quality Scan\n")
        description_parts.append("• Printable\n")
        description_parts.append("• Searchable Text (OCR)\n")
        description_parts.append("• Compatible with all devices\n")
        
        # Add what's included - more comprehensive
        description_parts.append("\n✅ What's Included:\n")
        description_parts.append("• Complete Service/Owner Manual\n")
        description_parts.append("• Detailed Diagrams & Illustrations\n")
        description_parts.append("• Step-by-Step Instructions\n")
        description_parts.append("• Specifications & Technical Data\n")
        description_parts.append("• Wiring Diagrams\n")
        description_parts.append("• Maintenance Schedules\n")
        description_parts.append("• Troubleshooting Guide\n")
        description_parts.append("• Parts Catalog\n")
        description_parts.append("• Torque Specifications\n")
        
        # Add benefits section
        description_parts.append("\n💡 Why This Manual?\n")
        description_parts.append("• Save money on repairs and maintenance\n")
        description_parts.append("• DIY repairs made easy with clear instructions\n")
        description_parts.append("• Professional-grade information at your fingertips\n")
        description_parts.append("• Understand your equipment inside and out\n")
        description_parts.append("• Perfect for mechanics, technicians, and DIY enthusiasts\n")
        
        # Add sample content if available
        if extracted_text and len(extracted_text) > 200:
            description_parts.append("\n📝 Sample Content:\n")
            sample = extracted_text[:800]
            description_parts.append(f"{sample}...\n")
        
        # Add delivery info
        description_parts.append("\n🚚 Delivery:\n")
        description_parts.append("• Instant Digital Download\n")
        description_parts.append("• No Shipping Required\n")
        description_parts.append("• Download link available immediately after purchase\n")
        description_parts.append("• Access from any device\n")
        description_parts.append("• Print as many copies as you need\n")
        
        # Add compatibility
        description_parts.append("\n📱 Compatibility:\n")
        description_parts.append("• Works on Windows, Mac, iOS, Android\n")
        description_parts.append("• Requires PDF reader (free download available)\n")
        description_parts.append("• Can be printed on any standard printer\n")
        
        # Add disclaimer
        description_parts.append("\n⚠️ Note:\n")
        description_parts.append(
            "This is a digital product. No physical item will be shipped. "
            "You will receive a download link after purchase.\n\n"
        )
        description_parts.append(
            "This manual is in PDF format and can be viewed on any computer or mobile device. "
            "You can print pages as needed or the entire manual.\n\n"
        )
        
        description_parts.append("Please contact us if you have any questions!")
        
        return "".join(description_parts)
    
    def _extract_from_text(self, text: str) -> list:
        """
        Extract relevant information from text
        
        Args:
            text: Text to extract from
            
        Returns:
            List of extracted parts
        """
        parts = []
        
        # Look for manufacturer
        manufacturers = [
            'Honda', 'Yamaha', 'Polaris', 'Suzuki', 'Kawasaki', 'Can-Am',
            'Toro', 'Craftsman', 'John Deere', 'Husqvarna',
            'Kubota', 'Massey Ferguson', 'New Holland',
            'Generac', 'Champion', 'Westinghouse'
        ]
        
        text_upper = text.upper()
        for manufacturer in manufacturers:
            if manufacturer.upper() in text_upper:
                parts.append(manufacturer)
                break
        
        # Look for model pattern (letters + numbers)
        model_match = re.search(r'\b[A-Z]{2,}\d{2,}\b', text_upper)
        if model_match:
            parts.append(model_match.group())
        
        return parts
    
    def _clean_title(self, title: str) -> str:
        """
        Clean up title by removing unwanted characters
        
        Args:
            title: Title to clean
            
        Returns:
            Cleaned title
        """
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title)
        
        # Remove special characters except hyphens and spaces
        title = re.sub(r'[^\w\s-]', '', title)
        
        # Capitalize words
        title = title.title()
        
        return title.strip()
    
    def extract_equipment_type(self, text: str) -> Optional[str]:
        """
        Extract equipment type from text
        
        Args:
            text: Text to analyze
            
        Returns:
            Equipment type or None
        """
        text_lower = text.lower()
        
        equipment_types = {
            'atv': 'ATV',
            'utv': 'UTV',
            'quad': 'ATV',
            'side by side': 'UTV',
            'lawn mower': 'Lawn Mower',
            'riding mower': 'Riding Mower',
            'push mower': 'Push Mower',
            'zero turn': 'Zero Turn Mower',
            'tractor': 'Tractor',
            'compact tractor': 'Compact Tractor',
            'farm tractor': 'Farm Tractor',
            'generator': 'Generator',
            'portable generator': 'Portable Generator',
            'inverter generator': 'Inverter Generator'
        }
        
        for keyword, equipment_type in equipment_types.items():
            if keyword in text_lower:
                return equipment_type
        
        return None

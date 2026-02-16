"""
Test script for AI-based PDF metadata extraction
"""
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.processors.pdf_ai_extractor import PDFAIExtractor, extract_pdf_metadata


def test_ai_extractor():
    """Test the AI extractor with a sample PDF"""
    
    # Check if API key is configured
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("❌ GROQ_API_KEY not configured. Please set it in your .env file.")
        print("   Get a free API key from https://console.groq.com/")
        return
    
    print("✓ GROQ_API_KEY found")
    
    # Create extractor
    extractor = PDFAIExtractor()
    
    # Find a test PDF
    pdf_dir = Path('./data/pdfs')
    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {pdf_dir}")
        print("   Please place a test PDF in the data/pdfs directory")
        return
    
    # Find any PDF file
    pdf_files = list(pdf_dir.glob('*.pdf'))
    if not pdf_files:
        print(f"❌ No PDF files found in {pdf_dir}")
        return
    
    test_pdf = pdf_files[0]
    print(f"\n📄 Testing with PDF: {test_pdf.name}")
    print(f"   Size: {test_pdf.stat().st_size / 1024:.1f} KB")
    
    # Extract metadata
    print("\n🔍 Extracting metadata using AI...")
    result = extractor.extract_from_pdf(str(test_pdf))
    
    if result['success']:
        print("\n✓ Extraction successful!")
        print("\n📋 Extracted Metadata:")
        print(f"   Manufacturer: {result['manufacturer'] or 'Not found'}")
        print(f"   Model:        {result['model'] or 'Not found'}")
        print(f"   Year:         {result['year'] or 'Not found'}")
        print(f"   Title:        {result['title'] or 'Not found'}")
        
        # Generate filename from extracted data
        from app.utils import generate_safe_filename
        filename = generate_safe_filename(
            result['manufacturer'],
            result['model'],
            result['year']
        )
        print(f"\n📝 Generated filename: {filename}.pdf")
    else:
        print(f"\n❌ Extraction failed: {result['error']}")


def test_convenience_function():
    """Test the convenience function"""
    print("\n" + "="*60)
    print("Testing convenience function...")
    print("="*60)
    
    # Find a test PDF
    pdf_dir = Path('./data/pdfs')
    if not pdf_dir.exists():
        return
    
    pdf_files = list(pdf_dir.glob('*.pdf'))
    if not pdf_files:
        return
    
    test_pdf = pdf_files[0]
    
    result = extract_pdf_metadata(str(test_pdf))
    
    if result.get('success'):
        print(f"\n✓ Convenience function works!")
        print(f"   Manufacturer: {result.get('manufacturer') or 'Not found'}")
        print(f"   Model:        {result.get('model') or 'Not found'}")
        print(f"   Year:         {result.get('year') or 'Not found'}")


def test_availability_check():
    """Test the availability check"""
    print("\n" + "="*60)
    print("Testing availability check...")
    print("="*60)
    
    extractor = PDFAIExtractor()
    
    if extractor.is_available():
        print("✓ AI extractor is available (API key configured)")
    else:
        print("❌ AI extractor is not available (no API key)")


if __name__ == '__main__':
    print("="*60)
    print("AI-Based PDF Metadata Extraction Test")
    print("="*60)
    
    test_availability_check()
    test_ai_extractor()
    test_convenience_function()
    
    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

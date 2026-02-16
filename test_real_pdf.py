"""
Test AI extraction with a real PDF file
"""
import sys
import io
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.processors.pdf_ai_extractor import PDFAIExtractor

# Test with the Honda PDF
pdf_path = r"E:\Manuals to List\manual_4_extracted\Honda.pdf"

print("="*60)
print("AI-Based PDF Metadata Extraction - Real PDF Test")
print("="*60)
print(f"\nTesting with PDF: {pdf_path}")
print()

# Check if file exists
if not Path(pdf_path).exists():
    print(f"❌ PDF file not found: {pdf_path}")
    sys.exit(1)

# Create extractor
extractor = PDFAIExtractor()

# Check availability
if not extractor.is_available():
    print("❌ AI extractor not available (GROQ_API_KEY not configured)")
    sys.exit(1)

print("✓ AI extractor is available")
print()

# Extract metadata
print("🔍 Extracting metadata from PDF...")
result = extractor.extract_from_pdf(pdf_path)

print()
print("📋 Extraction Results:")
print("-" * 60)
print(f"Success:     {result['success']}")
print(f"Manufacturer: {result['manufacturer'] or 'Not found'}")
print(f"Model:        {result['model'] or 'Not found'}")
print(f"Year:         {result['year'] or 'Not found'}")
print(f"Title:        {result['title'] or 'Not found'}")

if result['error']:
    print(f"Error:        {result['error']}")

print("-" * 60)

# Generate filename
if result['success'] and (result['manufacturer'] or result['model'] or result['year']):
    from app.utils import generate_safe_filename
    filename = generate_safe_filename(
        result['manufacturer'],
        result['model'],
        result['year']
    )
    print(f"\n📝 Generated filename: {filename}.pdf")
else:
    print("\n⚠️  Could not generate meaningful filename from extracted data")

print("\n" + "="*60)
print("Test completed!")
print("="*60)

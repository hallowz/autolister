"""Test the entire pipeline with Honda.pdf to identify filename issues"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Import only what we need directly to avoid dependency issues
from app.processors.pdf_processor import PDFProcessor
from app.utils import generate_safe_filename, parse_make_model_modelnumber

# Test file path
pdf_path = r"E:\Manuals to List\manual_4_extracted\Honda.pdf"

print("=" * 80)
print("Testing Pipeline with Honda.pdf")
print("=" * 80)

# Step 1: Extract metadata from PDF
print("\n1. Extracting PDF metadata...")
processor = PDFProcessor()
pdf_metadata = processor.extract_metadata(pdf_path)
print(f"   PDF Metadata: {pdf_metadata}")

# Step 2: Extract text from first page
print("\n2. Extracting text from first page...")
text = processor.extract_first_page_text(pdf_path)
print(f"   First page text (first 200 chars): {text[:200] if text else 'None'}...")

# Step 3: Parse filename
print("\n3. Parsing filename...")
pdf_filename = Path(pdf_path).stem
print(f"   PDF filename: {pdf_filename}")

# Try to extract from filename
parsed_from_filename = parse_make_model_modelnumber(pdf_filename)
print(f"   Parsed from filename: {parsed_from_filename}")

# Step 4: Test generate_safe_filename with different inputs
print("\n4. Testing generate_safe_filename with different inputs...")

# Test 1: Using only filename
result1 = generate_safe_filename(title=pdf_filename)
print(f"   Using filename only: {result1}")

# Test 2: Using PDF metadata
result2 = generate_safe_filename(
    manufacturer=pdf_metadata.get('manufacturer'),
    model=pdf_metadata.get('model'),
    year=pdf_metadata.get('year')
)
print(f"   Using PDF metadata: {result2}")

# Test 3: Using parsed filename data
result3 = generate_safe_filename(
    manufacturer=parsed_from_filename.get('make'),
    model=parsed_from_filename.get('model'),
    model_number=parsed_from_filename.get('model_number'),
    year=parsed_from_filename.get('year')
)
print(f"   Using parsed filename: {result3}")

# Step 5: Test generate_listing_images
print("\n5. Testing generate_listing_images...")
try:
    images = processor.generate_listing_images(
        pdf_path,
        manual_id=999,  # Test ID
        manufacturer=parsed_from_filename.get('make'),
        model=parsed_from_filename.get('model'),
        model_number=parsed_from_filename.get('model_number'),
        year=parsed_from_filename.get('year')
    )
    print(f"   Main images: {images['main']}")
    print(f"   Additional images: {images['additional']}")
except Exception as e:
    print(f"   Error generating images: {e}")

# Step 6: Check what the actual manual record would look like
print("\n6. Simulating manual record...")
manual_data = {
    'manufacturer': parsed_from_filename.get('make'),
    'model': parsed_from_filename.get('model'),
    'year': parsed_from_filename.get('year'),
    'title': pdf_metadata.get('title') or pdf_filename
}
print(f"   Manual data: {manual_data}")

# Extract model_number from model
import re
model_number = None
if manual_data['model']:
    number_match = re.search(r'\d+', manual_data['model'])
    if number_match:
        model_number = number_match.group()
print(f"   Extracted model_number: {model_number}")

# Generate final filename
final_filename = generate_safe_filename(
    manufacturer=manual_data['manufacturer'],
    model=manual_data['model'],
    model_number=model_number,
    year=manual_data['year'],
    title=manual_data['title']
)
print(f"   Final filename: {final_filename}")

print("\n" + "=" * 80)
print("Pipeline test complete!")
print("=" * 80)

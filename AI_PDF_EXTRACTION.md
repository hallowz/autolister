# AI-Based PDF Metadata Extraction

## Overview

This document describes the new AI-based PDF metadata extraction feature that uses the free Groq API to extract manufacturer, model, year, and title information directly from PDF pages.

## What Was Changed

### New Files Created

1. **[`app/processors/pdf_ai_extractor.py`](app/processors/pdf_ai_extractor.py)** - Main AI extraction module
   - `PDFAIExtractor` class for extracting metadata from PDFs
   - Uses Groq API with Llama 3.2 90B model (free tier)
   - Extracts: manufacturer, model, year, title
   - Graceful fallback when API is unavailable

2. **[`test_ai_unit.py`](test_ai_unit.py)** - Unit tests for the AI extractor
   - Tests string cleaning, year cleaning, availability checks
   - Tests AI metadata extraction with mocked API responses
   - Tests error handling (no API key, file not found)

3. **[`test_ai_extraction.py`](test_ai_extraction.py)** - Integration test script
   - Tests with real PDF files
   - Requires `GROQ_API_KEY` to be configured

### Modified Files

1. **[`app/processors/pdf_handler.py`](app/processors/pdf_handler.py)**
   - Added import for `PDFAIExtractor`
   - Initialized `ai_extractor` in `__init__`
   - Modified `download()` method to use AI extraction after download
   - Added `_generate_filename_with_ai()` method for AI-based filename generation

2. **[`app/config.py`](app/config.py)**
   - Added `groq_api_key: str = ""` field to Settings class

3. **[`.env`](.env)**
   - Added `GROQ_API_KEY=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`

4. **[`.env.example`](.env.example)**
   - Added `GROQ_API_KEY=your_groq_api_key_here` with instructions

## How It Works

### Download Flow

1. PDF is downloaded with a temporary filename based on URL
2. After successful download and validation, AI extractor analyzes the PDF
3. AI extracts metadata from the first 3 pages (where title info typically appears)
4. If AI extraction succeeds and produces meaningful data, the file is renamed
5. If AI extraction fails or returns no useful data, the original filename is kept

### AI Extraction Process

1. **Text Extraction**: Uses PyPDF2 (or pdfplumber as fallback) to extract text from PDF pages
2. **AI Analysis**: Sends extracted text to Groq API with a structured prompt
3. **Response Parsing**: Parses JSON response containing manufacturer, model, year, title
4. **Validation**: Cleans and validates extracted values
5. **Filename Generation**: Uses existing `generate_safe_filename()` utility to create meaningful filename

### API Details

- **Provider**: Groq (https://console.groq.com/)
- **Model**: `llama-3.3-70b-versatile`
- **Cost**: Free tier (no charge for usage)
- **Rate Limits**: Generous free tier limits
- **Response Format**: JSON with structured metadata

## Configuration

### Required Environment Variables

```bash
# Add to .env file
GROQ_API_KEY=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
```

### Getting a Groq API Key

1. Visit https://console.groq.com/
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Add the key to your `.env` file

## Usage

### Programmatic Usage

```python
from app.processors.pdf_ai_extractor import PDFAIExtractor

# Create extractor
extractor = PDFAIExtractor()

# Extract metadata from PDF
result = extractor.extract_from_pdf('path/to/manual.pdf')

if result['success']:
    print(f"Manufacturer: {result['manufacturer']}")
    print(f"Model: {result['model']}")
    print(f"Year: {result['year']}")
    print(f"Title: {result['title']}")
else:
    print(f"Error: {result['error']}")
```

### Convenience Function

```python
from app.processors.pdf_ai_extractor import extract_pdf_metadata

result = extract_pdf_metadata('path/to/manual.pdf')
```

### Automatic Usage

The AI extractor is automatically used by [`PDFDownloader`](app/processors/pdf_handler.py:15) when downloading PDFs. No code changes needed in existing workflows.

## Testing

### Run Unit Tests

```bash
python test_ai_unit.py
```

### Run Integration Tests (requires real PDF)

```bash
# Place a PDF in data/pdfs/ directory
python test_ai_extraction.py
```

## Benefits

1. **More Accurate Filenames**: AI understands context and extracts correct manufacturer/model info
2. **Handles Edge Cases**: Works with various PDF formats and naming conventions
3. **Graceful Degradation**: Falls back to existing regex-based extraction if AI fails
4. **Free to Use**: No API costs with Groq's generous free tier
5. **Easy to Configure**: Just add API key to `.env` file

## Limitations

1. **Requires API Key**: Must configure `GROQ_API_KEY` in environment
2. **Internet Connection**: Requires internet access to call Groq API
3. **Processing Time**: Adds ~1-2 seconds per PDF for AI analysis
4. **First Pages Only**: Only analyzes first 3 pages (where title info typically appears)

## Troubleshooting

### AI Extraction Not Working

1. Check that `GROQ_API_KEY` is set in `.env`
2. Verify internet connection
3. Check logs for error messages
4. Run `python test_ai_unit.py` to verify configuration

### PDFs Still Have Generic Names

1. AI extraction may have failed - check logs
2. PDF may not have extractable text (scanned images)
3. AI may not have recognized the manufacturer/model
4. Fallback to URL-based extraction is used in these cases

## Future Enhancements

- Add support for OCR (for scanned PDFs)
- Cache AI results to avoid re-processing
- Add retry logic for API failures
- Support multiple AI providers for redundancy
- Extract additional metadata (categories, keywords, etc.)

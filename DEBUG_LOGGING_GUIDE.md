# Debug Logging Guide for Filename Generation

This document explains the debug logging that has been added to help troubleshoot why incorrect file names are used when downloading resources.

## Overview

Debug logging has been added to the following files to track the complete filename generation process:

1. **app/processors/pdf_handler.py** - PDF download and filename generation
2. **app/utils/filename_utils.py** - Filename parsing and generation utilities
3. **app/api/routes.py** - API endpoints that trigger downloads
4. **app/tasks/jobs.py** - Background job processing for downloads

## Debug Logging Locations

### 1. PDFDownloader.download() (app/processors/pdf_handler.py)

**Location**: Lines 26-112

**What it logs**:
- Initial input parameters (URL, manual_id, manufacturer, model, year)
- URL validation status
- Temporary filename generated
- AI-generated filename (if applicable)
- Final filepath after any renaming

**Example output**:
```
[PDFDownloader.download] Starting download
[PDFDownloader.download] URL: https://example.com/manual.pdf
[PDFDownloader.download] manual_id: 123
[PDFDownloader.download] manufacturer: Honda
[PDFDownloader.download] model: Civic
[PDFDownloader.download] year: 2020
[PDFDownloader.download] Generated temp filename: 2020_Honda_Civic.pdf
[PDFDownloader.download] AI-generated filename: 2020_Honda_Civic.pdf
[PDFDownloader.download] Final filepath: /path/to/pdfs/2020_Honda_Civic.pdf
```

### 2. PDFDownloader._generate_filename() (app/processors/pdf_handler.py)

**Location**: Lines 134-193

**What it logs**:
- Input parameters received
- URL parts being parsed
- Extracted year from URL
- Extracted model from URL
- Extracted model number from model
- Final values before generating filename
- Safe filename generation result
- Fallback filename if needed

**Example output**:
```
[_generate_filename] Input parameters:
  url: https://example.com/Honda_Civic_2020.pdf
  manual_id: 123
  manufacturer: Honda
  model: Civic
  year: 2020
[_generate_filename] Extracting model/year from URL...
[_generate_filename] URL parts: ['https:', '', 'example.com', 'Honda_Civic_2020.pdf']
[_generate_filename] Extracted year from URL part 'Honda_Civic_2020.pdf': 2020
[_generate_filename] Extracted model from URL part 'Honda_Civic_2020.pdf': HONDA_CIVIC
[_generate_filename] After URL extraction:
  manufacturer: Honda
  model: HONDA_CIVIC
  model_number: 2020
  year: 2020
[_generate_filename] Generating safe filename from metadata...
```

### 3. PDFDownloader._generate_filename_with_ai() (app/processors/pdf_handler.py)

**Location**: Lines 195-251

**What it logs**:
- Input parameters
- AI extraction availability status
- AI extraction results
- Final AI-extracted values
- Generated filename from AI data

**Example output**:
```
[_generate_filename_with_ai] Input parameters:
  filepath: /path/to/pdfs/temp.pdf
  url: https://example.com/manual.pdf
  manufacturer: Honda
  model: Civic
  year: 2020
[_generate_filename_with_ai] Extracting metadata from PDF with AI...
[_generate_filename_with_ai] AI extraction result: {'success': True, 'manufacturer': 'Honda', 'model': 'Civic', 'year': '2020'}
[_generate_filename_with_ai] AI-extracted/final values:
  ai_manufacturer: Honda
  ai_model: Civic
  ai_year: 2020
[_generate_filename_with_ai] Generating safe filename from AI data...
```

### 4. generate_safe_filename() (app/utils/filename_utils.py)

**Location**: Lines 202-268

**What it logs**:
- Input parameters (manufacturer, model, year, title, fallback)
- Title parsing results
- Alphanumeric pattern extraction
- Final values before building parts
- Individual parts being added (year, manufacturer, model)
- Final result

**Example output**:
```
[generate_safe_filename] === START ===
[generate_safe_filename] Input: manufacturer=Honda, model=Civic, year=2020, title=None, fallback=manual
[generate_safe_filename] Final values before building parts:
  manufacturer: 'Honda'
  model: 'Civic'
  year: '2020'
[generate_safe_filename] Added year part: '2020'
[generate_safe_filename] Added manufacturer part: 'Honda'
[generate_safe_filename] Added model part: 'Civic' (original: 'Civic')
[generate_safe_filename] Parts list: ['2020', 'Honda', 'Civic']
[generate_safe_filename] Result: '2020_Honda_Civic'
[generate_safe_filename] === END ===
```

### 5. parse_make_model_modelnumber() (app/utils/filename_utils.py)

**Location**: Lines 8-121

**What it logs**:
- Input title and manufacturer
- Manufacturer found in title
- Cleaned title after manufacturer removal
- Model extraction results
- Final parsed result

**Example output**:
```
[parse_make_model_modelnumber] === START ===
[parse_make_model_modelnumber] Input: title='Honda Civic 2020 Service Manual', manufacturer=None
[parse_make_model_modelnumber] Found manufacturer 'Honda', cleaned title: 'Civic 2020 Service Manual'
[parse_make_model_modelnumber] Result: {'make': 'Honda', 'model': 'Civic', 'model_number': '2020'}
[parse_make_model_modelnumber] === END ===
```

### 6. API Routes (app/api/routes.py)

**approve_manual()** (Lines 407-416):
```
[approve_manual] Approving manual_id=123
[approve_manual] Manual details:
  source_url: https://example.com/manual.pdf
  title: Honda Civic 2020 Service Manual
  manufacturer: Honda
  model: Civic
  year: 2020
```

**download_manual()** (Lines 495-507):
```
[download_manual] Downloading PDF for manual_id=123
[download_manual] Manual details:
  source_url: https://example.com/manual.pdf
  title: Honda Civic 2020 Service Manual
  manufacturer: Honda
  model: Civic
  year: 2020
```

### 7. Background Jobs (app/tasks/jobs.py)

**process_approved_manuals()** (Lines 132-141):
```
[process_approved_manuals] Processing manual_id=123
[process_approved_manuals] Manual details:
  source_url: https://example.com/manual.pdf
  title: Honda Civic 2020 Service Manual
  manufacturer: Honda
  model: Civic
  year: 2020
```

**process_single_manual()** (Lines 344-353):
```
[process_single_manual] Processing manual_id=123
[process_single_manual] Manual details:
  source_url: https://example.com/manual.pdf
  title: Honda Civic 2020 Service Manual
  manufacturer: Honda
  model: Civic
  year: 2020
```

## How to Use the Debug Logging

### 1. Enable Debug Output

The debug logging uses `print()` statements, so it will appear in your console output when running the application.

### 2. Trigger a Download

Download a manual through any of the following methods:
- API endpoint: `POST /api/manuals/{manual_id}/approve`
- API endpoint: `POST /api/manuals/{manual_id}/download`
- Background job: `process_approved_manuals()`
- Background job: `process_single_manual(manual_id)`

### 3. Analyze the Output

Follow the flow of logs to understand:
1. What parameters are being passed to the download function
2. How the URL is being parsed for model/year
3. How the filename is being generated from metadata
4. Whether AI extraction is being used
5. What the final filename is

### 4. Identify Issues

Common issues to look for:

**Missing Parameters**:
```
[PDFDownloader.download] manufacturer: None
[PDFDownloader.download] model: None
[PDFDownloader.download] year: None
```
This indicates the database doesn't have the metadata filled in.

**URL Extraction Failing**:
```
[_generate_filename] Extracting model/year from URL...
[_generate_filename] URL parts: ['https:', '', 'example.com', 'file.pdf']
```
No model/year found in URL, will use hash-based fallback.

**Title Parsing Issues**:
```
[parse_make_model_modelnumber] Input: title='Some Random Title', manufacturer=None
[parse_make_model_modelnumber] Result: {'make': None, 'model': None, 'model_number': None}
```
Title doesn't contain recognizable manufacturer/model.

**Fallback to Hash**:
```
[_generate_filename] Using hash-based filename fallback
[_generate_filename] Returning fallback filename: manual_a1b2c3d4e5f6.pdf
```
No meaningful metadata available, using hash-based filename.

## Common Problems and Solutions

### Problem 1: All files have hash-based names like `manual_a1b2c3d4e5f6.pdf`

**Cause**: No metadata (manufacturer, model, year) is available in the database or URL.

**Solution**: 
- Ensure manual records have manufacturer, model, and year filled in
- Improve URL parsing patterns in `_generate_filename()`
- Improve title parsing in `parse_make_model_modelnumber()`

### Problem 2: Wrong manufacturer in filename

**Cause**: Title parsing is matching the wrong manufacturer or URL extraction is incorrect.

**Solution**:
- Check the `[parse_make_model_modelnumber]` logs to see which manufacturer was matched
- Review the common_manufacturers list in `filename_utils.py`
- Check URL extraction logs to see if model is being extracted from URL

### Problem 3: Model name is wrong or missing

**Cause**: Model extraction patterns don't match the actual model format.

**Solution**:
- Check the `[_generate_filename]` logs to see what model was extracted from URL
- Check the `[generate_safe_filename]` logs to see what model is being used
- Review the model extraction patterns in `parse_make_model_modelnumber()`

### Problem 4: Year is wrong or missing

**Cause**: Year extraction pattern doesn't match or year is not in the expected format.

**Solution**:
- Check the `[_generate_filename]` logs to see what year was extracted from URL
- Check the `[generate_safe_filename]` logs to see what year is being used
- Ensure year is in format YYYY (e.g., 2020, not 20)

## Removing Debug Logging

Once you've identified and fixed the issue, you can remove the debug logging by:

1. Removing all `print()` statements with the debug prefixes:
   - `[PDFDownloader.download]`
   - `[_generate_filename]`
   - `[_generate_filename_with_ai]`
   - `[generate_safe_filename]`
   - `[parse_make_model_modelnumber]`
   - `[approve_manual]`
   - `[download_manual]`
   - `[process_approved_manuals]`
   - `[process_single_manual]`

2. Or, you can leave them in for future debugging and redirect output to a log file.

## Additional Notes

- The debug logging is designed to be non-intrusive and won't affect functionality
- All logs include clear prefixes to make filtering easier
- The logging follows the complete flow from API call to final filename
- You can use `grep` or similar tools to filter specific log sections

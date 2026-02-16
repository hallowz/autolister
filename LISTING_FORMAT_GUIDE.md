# Etsy Listing Format Guide

This document describes the new AI-generated Etsy listing format for AutoLister.

## Overview

The AutoLister now generates SEO-optimized Etsy listings using AI analysis of PDF content. The listing format follows the structure of successful Etsy listings for service manuals.

## Listing Components

### 1. SEO-Optimized Title

**Format:** `[Manufacturer] [Model] Service Manual | [Year Range] [Vehicle Type] Repair Guide | Instant Digital Download | PDF`

**Example:** `Honda Pioneer SXS700 M2/M4 Service Manual | 2014–2024 UTV Repair Guide | Instant Digital Download | PDF`

**Key Features:**
- Pipe-separated sections for readability
- Includes manufacturer and model at the start
- Year range or single year
- Vehicle type (UTV, ATV, Motorcycle, Car, Truck, etc.)
- Ends with "Instant Digital Download | PDF"
- Under 140 characters for optimal Etsy display
- Keyword-rich for search optimization

### 2. Detailed Description

The description follows this structure:

```
[Year] [Manufacturer] [Model] SERVICE MANUAL
• [Manufacturer] original service manual
• Adobe Acrobat (PDF) format
• Fully Searchable
• Easily print any or all content
• Provided via direct download shortly after purchase
• Everything needed to repair & maintain your motor
• Troubleshooting instructions, diagrams and reference material.

MODELS COVERED:
• [List all model variants]
• All Models [Year range]

TABLE OF CONTENTS ([Page Count] Pages)
[Extracted table of contents from PDF]

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
```

### 3. Tags

The system generates 13 relevant Etsy tags (maximum allowed by Etsy):

**Tag Categories:**
1. Manufacturer name (e.g., "Honda")
2. Model name/number (e.g., "Pioneer 700")
3. Year (e.g., "2014")
4. Product type (e.g., "Service Manual")
5. Vehicle type (e.g., "UTV")
6. Keywords (e.g., "Repair Guide", "PDF", "Digital Download")
7. Format (e.g., "OEM", "Workshop Manual")
8. Additional relevant terms

**Example Tags:**
```
["Honda", "Pioneer 700", "Service Manual", "UTV", "Repair Guide", "PDF", 
 "Digital Download", "OEM", "Workshop Manual", "2014", "SXS700", 
 "Manual", "Honda Pioneer"]
```

## Implementation

### New Files Created

1. **`app/processors/listing_generator.py`** - Main module for generating listing content
   - `ListingContentGenerator` class
   - Methods for generating SEO titles, descriptions, and tags
   - Uses Groq API (llama-3.3-70b-versatile model)

2. **`migrations/add_listing_fields.py`** - Database migration script
   - Adds `description` and `tags` columns to the `manuals` table

### Modified Files

1. **`app/database.py`** - Added `description` and `tags` fields to `Manual` model

2. **`app/tasks/jobs.py`** - Updated processing workflow:
   - `process_single_manual()` - Now uses `ListingContentGenerator`
   - `create_etsy_listings()` - Updated to use pre-generated content
   - `generate_resources_zip()` - Creates unified `LISTING_DATA.txt` file

3. **`app/etsy/listing.py`** - Updated `create_digital_listing()` to accept tags parameter

### Resource File Format

The resources zip now contains a single `LISTING_DATA.txt` file instead of separate README and description files. This file includes:

- SEO Title
- Description
- Tags
- Manual Information
- Files Included
- Etsy Listing Instructions
- Tips for Success

## Usage

### Running the Migration

Before using the new listing format, run the migration script:

```bash
python migrations/add_listing_fields.py
```

### Processing Manuals

When processing manuals, the system will automatically:

1. Extract text from the PDF
2. Use AI to analyze the content
3. Generate SEO-optimized title
4. Generate detailed description
5. Generate 13 relevant tags
6. Save all content to the database
7. Create resources zip with LISTING_DATA.txt

### Creating Etsy Listings

The `create_etsy_listings()` function will:

1. Use pre-generated title, description, and tags from the database
2. Generate images if needed
3. Create the Etsy listing with all content
4. Upload images and PDF file

## AI Prompts

### Title Generation Prompt

The system uses a structured prompt to generate SEO-optimized titles:

```
Create a compelling, SEO-optimized title following this EXACT format:
"[Manufacturer] [Model] Service Manual | [Year Range] [Vehicle Type] Repair Guide | Instant Digital Download | PDF"

Rules:
- Use pipe symbols (|) to separate sections
- Include the manufacturer and model at the start
- Include year range if multiple years are mentioned
- Include vehicle type (UTV, ATV, Motorcycle, Car, Truck, etc.)
- End with "Instant Digital Download | PDF"
- Keep it under 140 characters if possible
- Make it keyword-rich for Etsy search
```

### Description Generation Prompt

The description prompt follows the exact format shown above, extracting real information from the PDF including:

- Models covered
- Table of contents
- Page count
- Specific procedures mentioned

### Tags Generation Prompt

The tags prompt ensures:

- 13 tags maximum (Etsy limit)
- 1-3 words per tag
- 20 characters or less when possible
- Keyword-rich for search
- Includes manufacturer, model, year, vehicle type, and relevant keywords

## Configuration

The system uses the Groq API for AI generation. Ensure your `.env` file contains:

```
GROQ_API_KEY=your_api_key_here
```

The model used is `llama-3.3-70b-versatile` (free tier).

## Benefits

1. **SEO Optimization**: Titles and tags are optimized for Etsy search
2. **Professional Format**: Descriptions follow proven successful listing formats
3. **Accurate Content**: AI extracts real information from PDFs
4. **Consistent Quality**: All listings follow the same professional structure
5. **Time Saving**: Automated generation reduces manual work
6. **Better Conversion**: Professional listings lead to more sales

## Troubleshooting

### AI Generation Fails

If AI generation fails, the system falls back to the old `SummaryGenerator` method.

### Missing API Key

If `GROQ_API_KEY` is not configured, the system will use fallback methods.

### Database Migration Issues

If the migration fails, ensure:
- The database file exists
- You have write permissions
- The database is not locked by another process

## Future Enhancements

Potential improvements:

- Add support for multiple languages
- Include more vehicle types in templates
- Add A/B testing for titles and descriptions
- Generate variations for different markets
- Add analytics to track listing performance

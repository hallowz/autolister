"""
AI-powered scrape configuration generator
Generates comprehensive scrape configurations from natural language prompts
"""
import json
from typing import Dict, Optional
from app.config import get_settings

settings = get_settings()


# Default exclude terms that should almost always be used
DEFAULT_EXCLUDE_TERMS = """preview,operator,operation,user manual,owner manual,owners manual,quick start,quickstart,brochure,catalog,sample,specifications only,cover,front cover,table of contents,advertisement,promotional"""


# The comprehensive AI prompt for generating scrape configurations
GENERATE_CONFIG_SYSTEM_PROMPT = """You are an expert at configuring web scraping jobs for finding PDF service manuals, repair guides, and technical documentation. Your goal is to generate COMPREHENSIVE scrape configurations that discover EXACTLY the files the user wants.

You MUST populate EVERY field with intelligent values based on the user's prompt. No field should be left as null unless truly unknown.

## OUTPUT FORMAT
Return ONLY valid JSON with these fields:

```json
{
  "name": "string - short descriptive name",
  "source_type": "string - always 'multi_site' for best results",
  "query": "string - search query with OR between terms",
  "max_results": "integer - number of results (default 100)",
  "equipment_type": "string or null - category of equipment",
  "manufacturer": "string or null - brand name",
  "model_patterns": "string or null - model patterns like 'TRX,FOCUS,CIVIC'",
  "year_range": "string or null - like '1990-2020' or '1970s'",
  "search_terms": "string - CRITICAL: terms that MUST appear in URL/filename/title",
  "exclude_terms": "string - CRITICAL: terms that should NOT appear",
  "file_extensions": "string - always 'pdf' unless user specifies otherwise",
  "min_pages": "integer - minimum page count (default 5 to avoid previews)",
  "max_pages": "integer or null - maximum page count if relevant",
  "min_file_size_mb": "float - minimum file size (default 0.5)",
  "max_file_size_mb": "float or null - maximum file size",
  "follow_links": "boolean - always true for comprehensive discovery",
  "max_depth": "integer - how deep to crawl (default 3)",
  "extract_directories": "boolean - always true to find PDF collections",
  "skip_duplicates": "boolean - always true",
  "sites": "string or null - specific sites if user mentioned any",
  "url_patterns": "string or null - URL patterns to match",
  "title_patterns": "string or null - patterns for file titles",
  "content_keywords": "string or null - expected keywords in PDF content",
  "priority": "integer - 1-10 (1=highest priority)",
  "description": "string - human readable description"
}
```

## CRITICAL RULES

### 1. SEARCH TERMS (MOST IMPORTANT)
These terms MUST appear in the URL, filename, or page title for a PDF to be included. Be VERY specific:

- **For service manuals**: Include "service manual", "repair manual", "workshop manual", "technical manual", "maintenance manual"
- **For specific equipment**: Include model numbers, part numbers, series names
- **For manufacturers**: Include brand name AND common abbreviations (Honda=HON, Yamaha=YAM)

Example for Honda ATV:
```
"search_terms": "service manual,repair manual,workshop manual,Honda,HON,TRX,ATV,utility vehicle,off-road,fourtrax,rancher,foreman"
```

### 2. EXCLUDE TERMS (ALWAYS SET THESE)
Always exclude files that are NOT what the user wants:

```
"exclude_terms": "preview,operator,operation,user manual,owner manual,owners manual,quick start,quickstart,brochure,catalog,sample,specifications only,cover,front cover,table of contents,advertisement,promotional,parts catalog,accessories,merchandise"
```

Add more based on what the user is NOT looking for:
- If looking for service manuals: add "user guide,getting started,warranty"
- If looking for older equipment: add "2024,2023,2022" (recent years)
- If looking for print quality: add "low resolution,web version"

### 3. FILE SIZE FILTERS
Set intelligent file size limits to avoid junk:

- **Service manuals**: min 0.5 MB, max 100 MB
- **Parts catalogs**: min 1 MB, max 200 MB
- **Quick guides**: min 0.1 MB, max 10 MB
- **Full documentation sets**: min 5 MB, no max

### 4. PAGE COUNT FILTERS
Use page count to filter out previews and incomplete documents:

- **Service manuals**: min 10 pages (real manuals are comprehensive)
- **Owner's manuals**: min 20 pages
- **Quick reference**: min 2 pages
- **Parts catalogs**: min 20 pages

### 5. MODEL PATTERNS
Extract ALL model numbers/patterns from the prompt:

User says: "Honda TRX420 and TRX500 Rancher and Foreman"
You set: "model_patterns": "TRX420,TRX500,Rancher,Foreman,TRX,FourTrax"

### 6. URL PATTERNS
Help identify good sources:

Common good patterns for service manuals:
- "*/service/*", "*/manual/*", "*/download/*", "*/docs/*", "*/library/*"
- "*.pdf", "*manual*.pdf", "*service*.pdf"

### 7. MANUFACTURER DETECTION
Extract manufacturer and common variations:

| User Says | Manufacturer | Also Include in Search |
|-----------|-------------|----------------------|
| Honda | Honda | HON, Honda Motor |
| Yamaha | Yamaha | YAM |
| Kawasaki | Kawasaki | KAW, KHI |
| Suzuki | Suzuki | SUZ |
| Polaris | Polaris | POL |
| John Deere | John Deere | JD, Deere |
| Canon | Canon | Canon Inc |
| Nikon | Nikon | Nikon Corp |
| Toyota | Toyota | TOY |

### 8. EQUIPMENT TYPE DETECTION

| Keywords | Equipment Type |
|----------|---------------|
| ATV, quad, four-wheeler | ATV |
| UTV, side-by-side, SxS, ranger, pioneer | UTV |
| motorcycle, bike, street bike, cruiser | Motorcycle |
| dirt bike, motocross, enduro | Dirt Bike |
| lawn mower, riding mower, push mower | Lawnmower |
| tractor, farm tractor, compact tractor | Tractor |
| generator, portable power, inverter | Generator |
| camera, DSLR, mirrorless, EOS, Nikon | Camera |
| car, truck, automobile, vehicle | Automotive |
| boat, marine, outboard, jet ski | Marine |
| snowmobile, sled, ski-doo | Snowmobile |
| RV, motorhome, camper | RV |
| aircraft, plane, helicopter | Aviation |

## EXAMPLE CONFIGURATIONS

### Example 1: Honda ATV Service Manuals
User prompt: "I need Honda ATV service manuals, specifically TRX420 Rancher and TRX500 Foreman models"

```json
{
  "name": "Honda ATV TRX420 TRX500 Service Manuals",
  "source_type": "multi_site",
  "query": "Honda TRX420 OR TRX500 OR Rancher OR Foreman service manual OR repair manual OR workshop manual",
  "max_results": 100,
  "equipment_type": "ATV",
  "manufacturer": "Honda",
  "model_patterns": "TRX420,TRX420FM,TRX420TM,TRX420FPM,TRX500,TRX500FA,TRX500FGA,Rancher,Foreman,FourTrax",
  "year_range": null,
  "search_terms": "service manual,repair manual,workshop manual,Honda,HON,TRX420,TRX500,Rancher,Foreman,ATV,fourtrax,utility ATV",
  "exclude_terms": "preview,operator,operation,user manual,owner manual,quick start,brochure,catalog,sample,parts list,accessories",
  "file_extensions": "pdf",
  "min_pages": 10,
  "max_pages": null,
  "min_file_size_mb": 1.0,
  "max_file_size_mb": 100,
  "follow_links": true,
  "max_depth": 3,
  "extract_directories": true,
  "skip_duplicates": true,
  "sites": null,
  "url_patterns": "*/service/*,*/manual/*,*/download/*,*/docs/*",
  "title_patterns": "service,repair,workshop,maintenance",
  "content_keywords": "torque,specifications,procedures,diagram,wiring",
  "priority": 5,
  "description": "Comprehensive Honda TRX420 Rancher and TRX500 Foreman service and repair manuals"
}
```

### Example 2: Vintage Canon Camera Manuals
User prompt: "Find vintage Canon camera service manuals from the 1970s and 1980s"

```json
{
  "name": "Vintage Canon Camera 1970s-1980s Service Manuals",
  "source_type": "multi_site",
  "query": "Canon camera service manual OR repair manual 1970s OR 1980s OR vintage OR film camera",
  "max_results": 100,
  "equipment_type": "Camera",
  "manufacturer": "Canon",
  "model_patterns": "AE-1,AT-1,AV-1,A-1,FTb,FT,Canonet,QL,Pellix,F-1,New F-1,T70,T80,T90,EOS",
  "year_range": "1970-1989",
  "search_terms": "service manual,repair manual,Canon,AE-1,AT-1,AV-1,A-1,F-1,FTb,film camera,vintage,classic camera,SLR,FD mount",
  "exclude_terms": "preview,digital,EOS digital,user manual,owner manual,quick start,brochure,catalog,sample,modern",
  "file_extensions": "pdf",
  "min_pages": 5,
  "max_pages": null,
  "min_file_size_mb": 0.5,
  "max_file_size_mb": 50,
  "follow_links": true,
  "max_depth": 3,
  "extract_directories": true,
  "skip_duplicates": true,
  "sites": null,
  "url_patterns": "*/service/*,*/manual/*,*/vintage/*,*/classic/*",
  "title_patterns": "Canon,AE-1,service,repair,manual,vintage",
  "content_keywords": "shutter,aperture,lens,film advance,exposure,canon",
  "priority": 5,
  "description": "Service and repair manuals for vintage Canon film cameras from the 1970s and 1980s including AE-1, F-1, A-1 series"
}
```

### Example 3: Small Engine Repair Manuals
User prompt: "Small engine repair manuals for Briggs Stratton and Tecumseh"

```json
{
  "name": "Briggs & Stratton Tecumseh Small Engine Service Manuals",
  "source_type": "multi_site",
  "query": "Briggs Stratton OR Tecumseh small engine service manual OR repair manual OR workshop manual",
  "max_results": 100,
  "equipment_type": "Small Engine",
  "manufacturer": "Briggs & Stratton, Tecumseh",
  "model_patterns": "Quantum,Intek,Vanguard,OHV,Horizontal,Vertical,flat head,L-head,DOV",
  "year_range": null,
  "search_terms": "service manual,repair manual,small engine,lawn mower engine,Briggs,Stratton,Tecumseh,OHV,engine repair,carburetor,tune up",
  "exclude_terms": "preview,parts catalog only,user manual,owner manual,quick start,brochure,safety guide",
  "file_extensions": "pdf",
  "min_pages": 10,
  "max_pages": null,
  "min_file_size_mb": 1.0,
  "max_file_size_mb": 100,
  "follow_links": true,
  "max_depth": 3,
  "extract_directories": true,
  "skip_duplicates": true,
  "sites": null,
  "url_patterns": "*/service/*,*/manual/*,*/engine/*,*/repair/*",
  "title_patterns": "service,repair,engine,Briggs,Tecumseh",
  "content_keywords": "torque,specs,carburetor,ignition,compression,valve",
  "priority": 5,
  "description": "Service and repair manuals for Briggs & Stratton and Tecumseh small engines used in lawn equipment"
}
```

### Example 4: Generic Service Manual Search
User prompt: "Find all kinds of service manuals for outdoor power equipment"

```json
{
  "name": "Outdoor Power Equipment Service Manuals Collection",
  "source_type": "multi_site",
  "query": "outdoor power equipment OR lawn equipment OR garden equipment service manual OR repair manual",
  "max_results": 150,
  "equipment_type": "Outdoor Power Equipment",
  "manufacturer": null,
  "model_patterns": null,
  "year_range": null,
  "search_terms": "service manual,repair manual,workshop manual,maintenance guide,troubleshooting,outdoor power,lawn mower,chainsaw,trimmer,blower,generator,pressure washer",
  "exclude_terms": "preview,operator manual,user guide,quick start,parts catalog only,brochure,advertisement",
  "file_extensions": "pdf",
  "min_pages": 10,
  "max_pages": null,
  "min_file_size_mb": 0.5,
  "max_file_size_mb": 150,
  "follow_links": true,
  "max_depth": 3,
  "extract_directories": true,
  "skip_duplicates": true,
  "sites": null,
  "url_patterns": "*/service/*,*/manual/*,*/support/*,*/docs/*",
  "title_patterns": "service,repair,maintenance,workshop",
  "content_keywords": "torque,specifications,assembly,disassembly,adjustment",
  "priority": 5,
  "description": "Broad collection of service and repair manuals for outdoor power equipment including mowers, chainsaws, generators, and more"
}
```

## FINAL CHECKLIST

Before returning your JSON, verify:

1. ✅ search_terms includes ALL relevant keywords from the user's prompt
2. ✅ exclude_terms blocks unwanted document types
3. ✅ min_pages is set high enough to avoid previews (at least 5, ideally 10 for service manuals)
4. ✅ min_file_size_mb filters out tiny preview files
5. ✅ model_patterns captures all mentioned models AND variations
6. ✅ manufacturer includes common abbreviations
7. ✅ description accurately summarizes what the job will find

Return ONLY the JSON object, no other text.
"""


def generate_scrape_config(prompt: str) -> Dict:
    """
    Generate a comprehensive scrape configuration from a natural language prompt.
    
    Args:
        prompt: Natural language description of what to scrape
        
    Returns:
        Dictionary with complete scrape configuration
    """
    try:
        from groq import Groq
        
        # Check if API key is configured
        if not settings.groq_api_key:
            return {
                'success': False,
                'error': 'GROQ_API_KEY not configured. Please set GROQ_API_KEY in your environment.'
            }
        
        # Initialize Groq client
        client = Groq(api_key=settings.groq_api_key)
        
        # Call Groq API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": GENERATE_CONFIG_SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate a scrape job configuration for: {prompt}"}
            ],
            temperature=0.3,  # Lower temperature for more consistent outputs
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        config_json = completion.choices[0].message.content
        config = json.loads(config_json)
        
        # Apply intelligent defaults for any missing fields
        config = apply_defaults(config)
        
        config['success'] = True
        return config
        
    except ImportError:
        return {
            'success': False,
            'error': 'Groq library not installed. Run: pip install groq'
        }
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': f'Failed to generate configuration: {str(e)}',
            'traceback': traceback.format_exc()
        }


def apply_defaults(config: Dict) -> Dict:
    """Apply intelligent defaults for any missing fields"""
    
    defaults = {
        'name': 'Service Manuals Collection',
        'source_type': 'multi_site',
        'query': 'service manual OR repair manual OR workshop manual',
        'max_results': 100,
        'equipment_type': None,
        'manufacturer': None,
        'model_patterns': None,
        'year_range': None,
        'search_terms': 'service manual, repair manual, workshop manual, technical manual',
        'exclude_terms': DEFAULT_EXCLUDE_TERMS,
        'file_extensions': 'pdf',
        'min_pages': 5,
        'max_pages': None,
        'min_file_size_mb': 0.5,
        'max_file_size_mb': 100,
        'follow_links': True,
        'max_depth': 3,
        'extract_directories': True,
        'skip_duplicates': True,
        'sites': None,
        'url_patterns': None,
        'title_patterns': None,
        'content_keywords': None,
        'priority': 5,
        'description': None
    }
    
    # Apply defaults only for missing keys
    for key, default_value in defaults.items():
        if key not in config or config[key] is None:
            config[key] = default_value
    
    # Ensure exclude_terms always has the basics
    if config.get('exclude_terms'):
        basic_excludes = ['preview', 'operator', 'operation', 'user manual', 'quick start']
        existing = [t.strip().lower() for t in config['exclude_terms'].split(',')]
        for term in basic_excludes:
            if term not in existing:
                config['exclude_terms'] = f"{config['exclude_terms']}, {term}"
    
    # Ensure min_pages is at least 5
    if config.get('min_pages', 0) < 5:
        config['min_pages'] = 5
    
    return config

"""
Utility functions for generating meaningful filenames
"""
import re
from typing import Optional, Dict, Tuple


def parse_make_model_modelnumber(title: str, manufacturer: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Parse make, model, and model number from a title
    
    Args:
        title: Manual title (e.g., "Honda Honda Sxs1000 Service Manual")
        manufacturer: Optional manufacturer name if already known
        
    Returns:
        Dictionary with 'make', 'model', 'model_number' keys
    """
    print(f"[parse_make_model_modelnumber] === START ===")
    print(f"[parse_make_model_modelnumber] Input: title='{title}', manufacturer='{manufacturer}'")
    
    if not title:
        print(f"[parse_make_model_modelnumber] No title provided, returning defaults")
        return {'make': None, 'model': None, 'model_number': None}
    
    result = {
        'make': manufacturer,
        'model': None,
        'model_number': None
    }
    
    # Common manufacturers (case-insensitive)
    common_manufacturers = [
        'Honda', 'Yamaha', 'Polaris', 'Suzuki', 'Kawasaki', 'Can-Am',
        'Toro', 'Craftsman', 'John Deere', 'Husqvarna',
        'Kubota', 'Massey Ferguson', 'New Holland',
        'Generac', 'Champion', 'Westinghouse', 'Briggs & Stratton',
        'Kohler', 'Tecumseh', 'Onan', 'Cummins', 'Perkins',
        'Cub Cadet', 'MTD', 'Ariens', 'Gravely', 'Scag',
        'Dixon', 'Bobcat', 'Case', 'Ford', 'New Holland',
        'International', 'Massey Ferguson', 'Allis Chalmers',
        'Deutz', 'Fendt', 'Valtra', 'Lamborghini', 'Same'
    ]
    
    title_clean = title.strip()
    
    # Extract make if not provided
    if not result['make']:
        title_upper = title_clean.upper()
        for maker in common_manufacturers:
            if maker.upper() in title_upper:
                result['make'] = maker
                # Remove manufacturer from title for model extraction
                # Handle both space and underscore separators
                title_clean = re.sub(r'(^|[_\s])' + re.escape(maker) + r'([_\s]|$)', r'\1\2', title_clean, flags=re.IGNORECASE)
                title_clean = re.sub(r'[_\s]+', '_', title_clean).strip('_')
                print(f"[parse_make_model_modelnumber] Found manufacturer '{maker}', cleaned title: '{title_clean}'")
                break
    
    # Remove .pdf extension if present
    title_clean = re.sub(r'\.pdf$', '', title_clean, flags=re.IGNORECASE)
    
    # Remove common words (handle both spaces and underscores)
    words_to_remove = ['manual', 'service', 'owner', 'handbook', 'guide', 'instructions', 'repair', 'maintenance']
    for word in words_to_remove:
        title_clean = re.sub(r'(^|[_\s])' + re.escape(word) + r'([_\s]|$)', r'\1\2', title_clean, flags=re.IGNORECASE)
    
    # Remove equipment type words (handle both spaces and underscores)
    equipment_words = ['atv', 'utv', 'quad', 'side', 'lawn', 'mower', 'tractor',
                     'generator', 'engine', 'motor', 'riding', 'push', 'zero',
                     'turn', 'compact', 'farm', 'portable', 'inverter']
    for word in equipment_words:
        title_clean = re.sub(r'(^|[_\s])' + re.escape(word) + r'([_\s]|$)', r'\1\2', title_clean, flags=re.IGNORECASE)
    
    # Clean up separators
    title_clean = re.sub(r'[_\s]+', '_', title_clean).strip('_')
    
    print(f"[parse_make_model_modelnumber] After removing common words: '{title_clean}'")
    
    # Extract model and model number
    
    # Pattern 1: Look for longer alphanumeric codes (e.g., TRX450R, TRX520FA5)
    # This should match patterns like "TRX520FA5" in "2024_TRX520FA5"
    model_pattern = r'(^|[_\s])([A-Za-z]{3,}\d{2,}[A-Za-z0-9]*)([_\s]|$)'
    model_match = re.search(model_pattern, title_clean)
    
    if model_match:
        full_model = model_match.group(2)
        result['model'] = full_model
        print(f"[parse_make_model_modelnumber] Pattern 1 matched model: '{full_model}'")
        
        # Extract model number (the numeric part)
        number_match = re.search(r'\d+', full_model)
        if number_match:
            result['model_number'] = number_match.group()
    else:
        # Pattern 2: Look for standalone alphanumeric codes (e.g., "D105", "Sxs1000")
        # This should be checked for shorter codes
        alnum_pattern = r'(^|[_\s])([A-Za-z]{1,2}\d{2,}[A-Za-z0-9]*)([_\s]|$)'
        alnum_match = re.search(alnum_pattern, title_clean)
        
        if alnum_match:
            full_model = alnum_match.group(2)
            result['model'] = full_model
            print(f"[parse_make_model_modelnumber] Pattern 2 matched model: '{full_model}'")
            
            # Extract model number (the numeric part)
            number_match = re.search(r'\d+', full_model)
            if number_match:
                result['model_number'] = number_match.group()
        
        if not result['model']:
            # Pattern 3: Look for word + number combination (e.g., "Grizzly 700", "Sportsman 500")
            # This handles cases where the model name is a word followed by a number
            word_number_pattern = r'(^|[_\s])([A-Za-z]{4,})([_\s])(\d{2,})([_\s]|$)'
            word_number_match = re.search(word_number_pattern, title_clean)
            
            if word_number_match:
                word_part = word_number_match.group(2)
                number_part = word_number_match.group(4)
                result['model'] = f"{word_part}{number_part}"
                result['model_number'] = number_part
                print(f"[parse_make_model_modelnumber] Pattern 3 matched model: '{result['model']}'")
        
        if not result['model']:
            # Fallback: try to extract any alphanumeric pattern from remaining text
            alnum_fallback = re.search(r'[A-Za-z]+\d+[A-Za-z0-9]*|\d+[A-Za-z]+[A-Za-z0-9]*', title_clean)
            if alnum_fallback:
                result['model'] = alnum_fallback.group()
                print(f"[parse_make_model_modelnumber] Fallback matched model: '{result['model']}'")
                
                # Try to extract number from it
                number_match = re.search(r'\d+', result['model'])
                if number_match:
                    result['model_number'] = number_match.group()
    
    print(f"[parse_make_model_modelnumber] Result: {result}")
    print(f"[parse_make_model_modelnumber] === END ===")
    return result


def extract_model_year_from_title(title: str) -> tuple:
    """
    Extract model and year from title if possible
    
    Args:
        title: Manual title
        
    Returns:
        Tuple of (model, year)
    """
    if not title:
        return None, None
    
    # Try to extract year (4 digits starting with 19 or 20)
    year_match = re.search(r'\b(19|20)\d{2}\b', title)
    year = year_match.group() if year_match else None
    
    # Remove year from title for model extraction
    title_without_year = re.sub(r'\b(19|20)\d{2}\b', '', title).strip()
    
    # Try to extract model (look for patterns like "Civic", "Accord", "Foreman Rubicon", etc.)
    model = None
    
    # Common car models (expand as needed)
    common_models = [
        'Civic', 'Accord', 'CR-V', 'Pilot', 'Odyssey', 'Fit', 'Insight',
        'Camry', 'Corolla', 'RAV4', 'Highlander', 'Sienna', 'Prius',
        'F-150', 'Mustang', 'Explorer', 'Escape', 'Focus', 'Fusion',
        'Silverado', 'Tahoe', 'Suburban', 'Malibu', 'Equinox',
        'Altima', 'Sentra', 'Pathfinder', 'Rogue', 'Frontier',
        'Wrangler', 'Cherokee', 'Grand Cherokee', 'Liberty', 'Compass',
        'Foreman Rubicon', 'Rancher', 'FourTrax', 'Pioneer', 'Recon',
        'TRX', 'Rincon', 'Rubicon', 'Foreman', 'Rancher'
    ]
    
    for model_name in common_models:
        if model_name.lower() in title_without_year.lower():
            model = model_name
            break
    
    # If no model found, try to extract from title (look for capitalized words after manufacturer)
    if not model and title_without_year:
        # Remove common words using regex (more portable than str.replace with flags)
        words_to_remove = ['manual', 'service', 'owner', 'handbook', 'guide', 'instructions']
        for word in words_to_remove:
            title_without_year = re.sub(r'\b' + re.escape(word) + r'\b', '', title_without_year, flags=re.IGNORECASE)
        
        # Split by spaces and look for multi-word models
        words = [w for w in title_without_year.split() if w.strip()]
        if len(words) >= 2:
            # Join first two words as potential model
            model = ' '.join(words[:2])
        elif words:
            model = words[0]
    
    return model, year


def generate_safe_filename(
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[str] = None,
    title: Optional[str] = None,
    fallback: str = "manual"
) -> str:
    """
    Generate a safe filename from manual metadata
    
    Args:
        manufacturer: Manufacturer name
        model: Model name
        year: Year
        title: Manual title (used as fallback for model/year extraction)
        fallback: Fallback name if no metadata is provided
        
    Returns:
        Safe filename string in format: year_make_model
    """
    parts = []
    
    # Debug logging
    print(f"[generate_safe_filename] === START ===")
    print(f"[generate_safe_filename] Input: manufacturer={manufacturer}, model={model}, year={year}, title={title}, fallback={fallback}")
    
    # If we don't have model or year, try to extract from title
    if not model and not year and title:
        print(f"[generate_safe_filename] No model/year provided, attempting to extract from title...")
        parsed = parse_make_model_modelnumber(title, manufacturer)
        print(f"[generate_safe_filename] Parsed from title: {parsed}")
        if not manufacturer and parsed.get('make'):
            manufacturer = parsed['make']
            print(f"[generate_safe_filename] Updated manufacturer from title: {manufacturer}")
        if not model and parsed.get('model'):
            model = parsed['model']
            print(f"[generate_safe_filename] Updated model from title: {model}")
        if not year:
            # Try to extract year from title
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            if year_match:
                year = year_match.group()
                print(f"[generate_safe_filename] Extracted year from title: {year}")
    
    # If we still don't have a model, try to extract any alphanumeric code from title
    if not model and title:
        print(f"[generate_safe_filename] Still no model, trying alphanumeric pattern extraction...")
        # Remove common words and look for alphanumeric patterns
        words_to_remove = ['manual', 'service', 'owner', 'handbook', 'guide', 'instructions', 'repair', 'maintenance', 'pdf']
        title_clean = title
        for word in words_to_remove:
            title_clean = re.sub(r'\b' + re.escape(word) + r'\b', '', title_clean, flags=re.IGNORECASE)
        title_clean = re.sub(r'[^\w\s]', '', title_clean).strip()
        print(f"[generate_safe_filename] Cleaned title for pattern matching: '{title_clean}'")
        
        # Look for alphanumeric patterns
        alnum_match = re.search(r'\b([A-Za-z]+\d+[A-Za-z0-9]*|\d+[A-Za-z]+[A-Za-z0-9]*)\b', title_clean)
        if alnum_match:
            model = alnum_match.group(1)
            print(f"[generate_safe_filename] Extracted model from alphanumeric pattern: {model}")
        else:
            print(f"[generate_safe_filename] No alphanumeric pattern found")
    
    print(f"[generate_safe_filename] Final values before building parts:")
    print(f"  manufacturer: '{manufacturer}'")
    print(f"  model: '{model}'")
    print(f"  year: '{year}'")
    
    # Build parts in order: year, make, model
    # Note: model_number is NOT added separately since it's typically part of the model name
    if year:
        year_part = re.sub(r'[^\w\s-]', '', year).strip().replace(' ', '_')
        parts.append(year_part)
        print(f"[generate_safe_filename] Added year part: '{year_part}'")
    if manufacturer:
        manufacturer_part = re.sub(r'[^\w\s-]', '', manufacturer).strip().replace(' ', '_')
        parts.append(manufacturer_part)
        print(f"[generate_safe_filename] Added manufacturer part: '{manufacturer_part}'")
    if model:
        # Remove .pdf extension if present in model
        model_clean = re.sub(r'\.pdf$', '', model, flags=re.IGNORECASE)
        model_part = re.sub(r'[^\w\s-]', '', model_clean).strip().replace(' ', '_')
        parts.append(model_part)
        print(f"[generate_safe_filename] Added model part: '{model_part}' (original: '{model}')")
    
    print(f"[generate_safe_filename] Parts list: {parts}")
    result = "_".join(parts) if parts else fallback
    print(f"[generate_safe_filename] Result: '{result}'")
    print(f"[generate_safe_filename] === END ===")
    return result

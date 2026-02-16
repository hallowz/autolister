"""
Utility functions for generating meaningful filenames
"""
import re
from typing import Optional


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
        Safe filename string
    """
    parts = []
    
    # If we don't have model or year, try to extract from title
    if not model and not year and title:
        extracted_model, extracted_year = extract_model_year_from_title(title)
        if not model:
            model = extracted_model
        if not year:
            year = extracted_year
    
    if manufacturer:
        parts.append(re.sub(r'[^\w\s-]', '', manufacturer).strip().replace(' ', '_'))
    if year:
        parts.append(re.sub(r'[^\w\s-]', '', year).strip().replace(' ', '_'))
    if model:
        parts.append(re.sub(r'[^\w\s-]', '', model).strip().replace(' ', '_'))
    
    # Return meaningful name if we have parts, otherwise fallback
    return "_".join(parts) if parts else fallback

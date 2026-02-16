"""
Utility functions for generating meaningful filenames
"""
import re
from typing import Optional


def generate_safe_filename(
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[str] = None,
    fallback: str = "manual"
) -> str:
    """
    Generate a safe filename from manual metadata
    
    Args:
        manufacturer: Manufacturer name
        model: Model name
        year: Year
        fallback: Fallback name if no metadata is provided
        
    Returns:
        Safe filename string
    """
    parts = []
    
    if manufacturer:
        parts.append(re.sub(r'[^\w\s-]', '', manufacturer).strip().replace(' ', '_'))
    if year:
        parts.append(re.sub(r'[^\w\s-]', '', year).strip().replace(' ', '_'))
    if model:
        parts.append(re.sub(r'[^\w\s-]', '', model).strip().replace(' ', '_'))
    
    # Return meaningful name if we have parts, otherwise fallback
    return "_".join(parts) if parts else fallback

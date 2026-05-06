import re
from typing import Optional

def normalize_to_crores(text: str) -> Optional[float]:
    """
    Normalizes Indian currency strings to a standard float representing Crores (Cr).
    Examples:
    - '52,00,000' -> 0.52
    - '52 lakhs' -> 0.52
    - '5.2 crores' -> 5.2
    - 'INR 5200000' -> 0.52
    - '₹5.2 Cr' -> 5.2
    - '187.4 Cr' -> 187.4
    """
    if not text:
        return None

    # Lowercase and clean string
    clean_text = text.lower().replace(",", "")
    
    # Extract the first numeric value
    match = re.search(r'[\d\.]+', clean_text)
    if not match:
        return None
        
    try:
        value = float(match.group())
    except ValueError:
        return None

    # Detect units
    if "cr" in clean_text or "crore" in clean_text:
        return value
    elif "lakh" in clean_text or "lac" in clean_text:
        return value / 100.0
    elif "k" in clean_text or "thousand" in clean_text:
        return value / 10000.0
    
    # If no unit is specified, assume it's absolute if it's large (e.g. > 100,000)
    # since Govt tenders usually deal in large numbers.
    if value >= 100000:
        return value / 10000000.0  # Convert raw absolute number to Crores
    elif value < 1000:
        # If it's a small number with no unit, it might already be in Crores in context,
        # but let's assume it's raw unless we're sure. 
        # Actually, for CA certs, if it just says 5.2, it's ambiguous. But we'll return as is.
        return value

    return value / 10000000.0

"""
ClaimLens AI — Parser Utilities
"""
import re


def extract_amount(text: str) -> float:
    """Extract monetary amount from text."""
    patterns = [
        r'Rs\.?\s*([\d,]+)',
        r'INR\s*([\d,]+)',
        r'([\d,]+)\s*(?:rupees|rs)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    return 0.0


def extract_registration(text: str) -> str:
    """Extract vehicle registration from text."""
    match = re.search(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}', text.upper())
    return match.group(0) if match else ''

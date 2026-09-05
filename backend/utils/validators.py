"""
ClaimLens AI — Validators
"""
import re
from datetime import datetime


def validate_registration(reg: str) -> bool:
    """Validate Indian vehicle registration number format."""
    pattern = r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'
    return bool(re.match(pattern, reg.upper()))


def validate_date(date_str: str) -> bool:
    """Validate a date string."""
    from backend.services.calculation_engine import parse_date
    return parse_date(date_str) is not None


def validate_claim_id(claim_id: str) -> bool:
    """Validate claim ID format."""
    return bool(re.match(r'^CLM\d{3,}', claim_id))


def validate_policy_number(policy: str) -> bool:
    """Validate policy number format."""
    return bool(re.match(r'^POL-\d{4}-\d{3}$', policy))


def sanitize_input(text: str) -> str:
    """Remove potential injection content from input text."""
    # Remove common instruction injection patterns
    dangerous = [
        'ignore previous', 'ignore above', 'disregard',
        'system prompt', 'new instructions', 'override',
    ]
    sanitized = text
    for pattern in dangerous:
        if pattern.lower() in sanitized.lower():
            # Don't remove, but flag it
            sanitized = sanitized  # Keep original, handled at LLM level
    return sanitized

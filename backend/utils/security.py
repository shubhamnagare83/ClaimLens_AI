"""
ClaimLens AI — Security Utilities
"""
import os


def get_api_key() -> str:
    """Get API key from environment."""
    return os.environ.get('GEMINI_API_KEY', '')


def is_key_configured() -> bool:
    """Check if API key is set."""
    return bool(get_api_key())

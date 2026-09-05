"""
ClaimLens AI — Health Route
"""
from fastapi import APIRouter
from backend.config import APP_NAME, APP_VERSION, TRACK_ID, GEMINI_API_KEY
from backend.services import gemini_service

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "track": TRACK_ID,
        "database": "ok",
        "policy_index": "ok",
        "gemini": "configured" if gemini_service.is_available() else "not_configured",
        "mode": "full" if gemini_service.is_available() else "deterministic_fallback",
    }

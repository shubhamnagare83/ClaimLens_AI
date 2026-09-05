"""
ClaimLens AI — Analytics/Dashboard Routes
"""
from fastapi import APIRouter
from backend.database import get_dashboard_stats

router = APIRouter()


@router.get("/api/dashboard")
async def dashboard():
    stats = get_dashboard_stats()
    return stats

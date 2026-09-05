"""
ClaimLens AI — Configuration
"""
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
POLICY_DIR = DATA_DIR / "policy"
CLAIMS_DIR = DATA_DIR / "claims"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
DATABASE_DIR = BASE_DIR / "database"
FRONTEND_DIR = BASE_DIR / "frontend"

# ─── Database ────────────────────────────────────────────
DATABASE_PATH = DATABASE_DIR / "claimlens.db"

# ─── Gemini ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

# ─── Application ─────────────────────────────────────────
APP_NAME = "ClaimLens AI"
APP_VERSION = "1.0.0"
TRACK_ID = "PS02"
HOST = "0.0.0.0"
PORT = 8000
SEED = 2026

# ─── Policy ──────────────────────────────────────────────
CLAIM_WINDOW_DAYS = 7
POLICY_ID = "CMSP-2026"

# ─── Thresholds ──────────────────────────────────────────
ESCALATION_CONFIDENCE_THRESHOLD = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.65
CRITICAL_CONTRADICTION_SEVERITY = "CRITICAL"
HIGH_CONTRADICTION_SEVERITY = "HIGH"

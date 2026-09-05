"""
ClaimLens AI — Main Application Entry Point
PS02: Insurance Claims Evidence Review Assistant

Start with: python app.py
Access at: http://localhost:8000
"""
import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONUTF8', '1')
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import APP_NAME, APP_VERSION, TRACK_ID, HOST, PORT, FRONTEND_DIR
from backend.database import init_database
from backend.services import gemini_service, policy_engine, retrieval_service
from backend.routes import health, claims, documents, review, analytics, ml, assistant

# ── Create FastAPI app ──
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="PS02 — Evidence-first Motor Insurance Claim Investigation",
)

# ── Register routes ──
app.include_router(health.router)
app.include_router(claims.router)
app.include_router(documents.router)
app.include_router(review.router)
app.include_router(analytics.router)
app.include_router(ml.router)
app.include_router(assistant.router)

# ── Serve frontend ──
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
SAMPLE_DOCS_DIR = Path(__file__).resolve().parent / "sample_documents"
if SAMPLE_DOCS_DIR.exists():
    app.mount("/sample_documents", StaticFiles(directory=str(SAMPLE_DOCS_DIR)), name="sample_documents")



@app.get("/banners/{filename}")
async def serve_banner(filename: str):
    banner_file = FRONTEND_DIR / "banners" / filename
    if banner_file.exists():
        return FileResponse(str(banner_file))
    return FileResponse(str(FRONTEND_DIR / "banners" / "banner_1.jpg"))



@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/app.js")
async def serve_js():
    return FileResponse(str(FRONTEND_DIR / "app.js"), media_type="application/javascript")


@app.get("/styles.css")
async def serve_css():
    return FileResponse(str(FRONTEND_DIR / "styles.css"), media_type="text/css")


def startup():
    """Initialize all services."""
    print("=" * 48)
    print(f"  {APP_NAME}")
    print(f"  {TRACK_ID} Insurance Claims Evidence Assistant")
    print("=" * 48)
    print()

    # Database
    if init_database():
        print("  [OK] Database initialized")
    else:
        print("  [!!] Database initialization failed")

    # Gemini
    gemini_service.init_gemini()

    # Policy
    if policy_engine.init_policy():
        pass  # Already prints
    else:
        print("  [!!] Policy loading failed")

    # Retrieval index
    retrieval_service.init_retrieval()

    # Load demo claims into DB if not already loaded
    _preload_demo_claims()

    print()
    print(f"  Application: http://localhost:{PORT}")
    print("=" * 48)
    print()


def _preload_demo_claims():
    """Pre-load a subset of demo claims into the database."""
    import csv
    from backend.config import CLAIMS_DIR
    from backend.database import get_claim, insert_claim, insert_document

    csv_path = CLAIMS_DIR / "claims_master.csv"
    if not csv_path.exists():
        print("  [!] Claims CSV not found — demo claims not loaded")
        return

    loaded = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            claim_id = row['claim_id']
            if get_claim(claim_id):
                loaded += 1
                continue

            claim_data = {
                'claim_id': claim_id,
                'policy_number': row.get('policy_number', ''),
                'customer_name': row.get('customer_name', ''),
                'vehicle_type': row.get('vehicle_type', 'Car'),
                'vehicle_registration': row.get('vehicle_registration', ''),
                'incident_type': row.get('incident_type', 'Accident'),
                'incident_date': row.get('incident_date', ''),
                'incident_time': row.get('incident_time', ''),
                'incident_location': row.get('incident_location', ''),
                'claim_date': row.get('claim_date', ''),
                'policy_start_date': row.get('policy_start_date', ''),
                'policy_end_date': row.get('policy_end_date', ''),
                'idv': float(row.get('idv', 0)),
                'repair_estimate': float(row.get('repair_estimate', 0)),
                'deductible': float(row.get('deductible', 0)),
                'status': 'PENDING',
                'scenario_type': row.get('scenario_type', ''),
                'expected_outcome': row.get('expected_outcome', ''),
                'difficulty': row.get('difficulty', ''),
            }
            insert_claim(claim_data)

            # Load documents from filesystem
            scenario_folder = {
                'CLEAN': 'accident' if row.get('incident_type') == 'Accident' else 'theft',
                'MISSING_DOCUMENT': 'missing_documents',
                'CONTRADICTION': 'contradictions',
                'EXCLUSION': 'exclusions',
                'AMBIGUOUS': 'ambiguous',
            }
            folder = scenario_folder.get(row.get('scenario_type', ''), 'accident')
            claim_dir = CLAIMS_DIR / folder / claim_id

            if claim_dir.exists():
                for doc_path in claim_dir.iterdir():
                    if doc_path.suffix == '.txt' and doc_path.stem not in ('ground_truth',):
                        content = doc_path.read_text(encoding='utf-8')
                        insert_document(claim_id, doc_path.stem, doc_path.name, content)

            loaded += 1

    print(f"  [OK] {loaded} demo claims loaded")


# Run startup
startup()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

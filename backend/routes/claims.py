"""
ClaimLens AI — Claims Routes
"""
import csv
import json
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.config import CLAIMS_DIR, DATA_DIR
from backend.database import (
    get_all_claims, get_claim, insert_claim, get_claim_documents,
    insert_document, get_latest_review, get_review_versions,
    get_extracted_facts, update_claim, delete_claim
)
from backend.services import audit_service
from backend.models import ClaimCreateRequest, ClaimUpdateRequest

router = APIRouter()


@router.get("/api/claims")
async def list_claims():
    claims = get_all_claims()
    return {"claims": claims, "total": len(claims)}


@router.get("/api/claims/{claim_id}")
async def get_claim_detail(claim_id: str):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    documents = get_claim_documents(claim_id)
    review = get_latest_review(claim_id)
    versions = get_review_versions(claim_id)
    facts = get_extracted_facts(claim_id)

    return {
        "claim": claim,
        "documents": documents,
        "review": review,
        "versions": [{"version": v['version'], "recommendation": v['recommendation'],
                       "created_at": v['created_at']} for v in versions],
        "facts": facts,
    }


@router.post("/api/claims")
async def create_claim(req: ClaimCreateRequest):
    claim_id = f"CLM{str(uuid.uuid4())[:8].upper()}"
    policy_number = req.policy_number or f"POL-2026-{str(uuid.uuid4())[:3].upper()}"

    claim_data = {
        'claim_id': claim_id,
        'policy_number': policy_number,
        'customer_name': req.customer_name,
        'vehicle_type': req.vehicle_type,
        'vehicle_registration': req.vehicle_registration,
        'incident_type': req.incident_type,
        'incident_date': req.incident_date,
        'incident_time': req.incident_time,
        'incident_location': req.incident_location,
        'claim_date': req.claim_date,
        'policy_start_date': req.policy_start_date or '2026-01-01',
        'policy_end_date': req.policy_end_date or '2027-01-01',
        'idv': req.idv or 500000.0,
        'repair_estimate': req.repair_estimate or 0.0,
        'deductible': req.deductible or (2000 if req.vehicle_type == 'Car' else 1000),
        'status': 'PENDING',
    }

    result = insert_claim(claim_data)
    if result:
        audit_service.log_claim_created(claim_id)

        # Generate claim form text document
        claim_form_text = f"""CLAIM FORM
Claim ID: {claim_id}
Policy Number: {policy_number}
Policy Period: {claim_data['policy_start_date']} to {claim_data['policy_end_date']}
Insured Name: {req.customer_name}
Vehicle Type: {req.vehicle_type}
Registration: {req.vehicle_registration}
Insured Declared Value (IDV): INR {req.idv:,.2f}

INCIDENT DETAILS:
Date of Incident: {req.incident_date}
Time of Incident: {req.incident_time or '14:30'}
Location: {req.incident_location or 'Main Road'}
Incident Type: {req.incident_type}
Date Claim Intimated: {req.claim_date}
Repair Estimate Amount: INR {req.repair_estimate:,.2f}

Claimant Statement:
{req.description or f"Vehicle was involved in {req.incident_type.lower()} at {req.incident_location}. Seeking claim compensation."}
"""
        insert_document(claim_id, 'claim_form', 'claim_form.txt', claim_form_text)
        audit_service.log_document_uploaded(claim_id, 'claim_form', 'claim_form.txt')

        # If description is provided, also store customer statement document
        if req.description:
            stmt_text = f"""CUSTOMER INCIDENT STATEMENT
Claim ID: {claim_id}
Customer Name: {req.customer_name}
Vehicle: {req.vehicle_registration} ({req.vehicle_type})
Incident Date: {req.incident_date} {req.incident_time}
Location: {req.incident_location}

Narrative Statement:
{req.description}

Signature: {req.customer_name}
Date: {req.claim_date}
"""
            insert_document(claim_id, 'customer_statement', 'customer_statement.txt', stmt_text)
            audit_service.log_document_uploaded(claim_id, 'customer_statement', 'customer_statement.txt')

        return {"claim_id": claim_id, "status": "created", "message": "Claim created successfully"}
    raise HTTPException(500, "Failed to create claim")


@router.put("/api/claims/{claim_id}")
async def update_claim_endpoint(claim_id: str, req: ClaimUpdateRequest):
    existing = get_claim(claim_id)
    if not existing:
        raise HTTPException(404, f"Claim {claim_id} not found")

    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields provided to update")

    success = update_claim(claim_id, updates)
    if success:
        audit_service.log_event(
            claim_id, "CLAIM_UPDATED",
            f"Claim details updated: {', '.join(updates.keys())}",
            details=updates
        )
        return {"claim_id": claim_id, "status": "updated", "updated_fields": list(updates.keys())}
    raise HTTPException(500, "Failed to update claim")


@router.delete("/api/claims/{claim_id}")
async def delete_claim_endpoint(claim_id: str):
    existing = get_claim(claim_id)
    if not existing:
        raise HTTPException(404, f"Claim {claim_id} not found")

    success = delete_claim(claim_id)
    if success:
        return {"claim_id": claim_id, "status": "deleted", "message": f"Claim {claim_id} deleted successfully"}
    raise HTTPException(500, "Failed to delete claim")



@router.post("/api/demo/{scenario}")
@router.get("/api/demo/{scenario}")
async def load_demo(scenario: str):
    """Load a demo claim scenario."""
    scenario_map = {
        'clean_accident': ('CLEAN', 'Accident'),
        'missing_documents': ('MISSING_DOCUMENT', None),
        'contradictory_evidence': ('CONTRADICTION', None),
        'policy_exclusion': ('EXCLUSION', None),
        'clean_theft': ('CLEAN', 'Theft'),
        'difficult_theft': ('MISSING_DOCUMENT', 'Theft'),
        'ambiguous': ('AMBIGUOUS', None),
    }

    if scenario not in scenario_map:
        raise HTTPException(400, f"Unknown scenario: {scenario}. Available: {list(scenario_map.keys())}")

    scenario_type, incident_filter = scenario_map[scenario]

    # Find a matching claim from the CSV
    csv_path = CLAIMS_DIR / "claims_master.csv"
    if not csv_path.exists():
        raise HTTPException(500, "Claims dataset not found")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['scenario_type'] == scenario_type:
                if incident_filter and row['incident_type'] != incident_filter:
                    continue
                if scenario == 'difficult_theft' and row['incident_type'] != 'Theft':
                    continue
                return await _load_claim_from_csv(row)

    raise HTTPException(404, f"No demo claim found for scenario: {scenario}")


async def _load_claim_from_csv(row: dict) -> dict:
    """Load a claim from CSV row and its documents from the filesystem."""
    claim_id = row['claim_id']

    # Check if claim already loaded
    existing = get_claim(claim_id)
    if existing and get_claim_documents(claim_id):
        return {"claim_id": claim_id, "status": "already_loaded", "message": f"Demo claim {claim_id} loaded"}

    # Insert claim
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
    audit_service.log_claim_created(claim_id)

    # Find and load documents
    scenario_folder_map = {
        'CLEAN': lambda: 'accident' if row.get('incident_type') == 'Accident' else 'theft',
        'MISSING_DOCUMENT': lambda: 'missing_documents',
        'CONTRADICTION': lambda: 'contradictions',
        'EXCLUSION': lambda: 'exclusions',
        'AMBIGUOUS': lambda: 'ambiguous',
    }

    folder_fn = scenario_folder_map.get(row.get('scenario_type', ''))
    folder = folder_fn() if folder_fn else 'accident'
    claim_dir = CLAIMS_DIR / folder / claim_id

    if claim_dir.exists():
        for doc_path in claim_dir.iterdir():
            if doc_path.suffix == '.txt' and doc_path.stem != 'ground_truth':
                doc_type = doc_path.stem
                content = doc_path.read_text(encoding='utf-8')
                insert_document(claim_id, doc_type, doc_path.name, content)
                audit_service.log_document_uploaded(claim_id, doc_type, doc_path.name)

    return {"claim_id": claim_id, "status": "loaded", "message": f"Demo claim {claim_id} loaded successfully"}

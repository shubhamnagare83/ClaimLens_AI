"""
ClaimLens AI — Review Routes
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_claim, get_latest_review, get_claim_documents
from backend.services import report_service, simulation_service, audit_service
from backend.models import SimulationRequest

router = APIRouter()


@router.post("/api/claims/{claim_id}/review")
async def run_review(claim_id: str):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    docs = get_claim_documents(claim_id)
    if not docs:
        raise HTTPException(400, f"No documents found for claim {claim_id}. Upload documents first.")

    report = report_service.run_full_review(claim_id)
    return report


@router.get("/api/claims/{claim_id}/report")
async def get_report(claim_id: str):
    review = get_latest_review(claim_id)
    if not review:
        raise HTTPException(404, f"No review found for claim {claim_id}. Run review first.")
    return review.get('report_json', {})


@router.get("/api/claims/{claim_id}/audit")
async def get_audit(claim_id: str):
    trail = audit_service.get_claim_audit_trail(claim_id)
    return {"claim_id": claim_id, "audit_trail": trail}


@router.post("/api/claims/{claim_id}/simulate")
async def simulate(claim_id: str, params: SimulationRequest):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    docs = get_claim_documents(claim_id)
    documents = {d['document_type']: d['content'] for d in docs}

    # Get extracted facts from the latest review
    review = get_latest_review(claim_id)
    facts = review.get('report_json', {}).get('facts', {}) if review else {}

    result = simulation_service.run_simulation(
        claim, documents, facts, params.model_dump(exclude_none=True)
    )
    audit_service.log_simulation(claim_id, params.model_dump(exclude_none=True),
                                  result.get('simulated_recommendation', ''))
    return result

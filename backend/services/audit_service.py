"""
ClaimLens AI — Audit Service
Records all events for claim audit trail.
"""
from backend.database import insert_audit_event, get_audit_trail


def log_event(claim_id: str, event_type: str, description: str, details: dict = None):
    """Record an audit event."""
    insert_audit_event(claim_id, event_type, description, details)


def log_claim_created(claim_id: str):
    log_event(claim_id, "CLAIM_CREATED", f"Claim {claim_id} created")

def log_document_uploaded(claim_id: str, doc_type: str, filename: str):
    log_event(claim_id, "DOCUMENT_UPLOADED", f"Document uploaded: {filename}",
              {"document_type": doc_type, "filename": filename})

def log_document_parsed(claim_id: str, doc_type: str):
    log_event(claim_id, "DOCUMENT_PARSED", f"Document parsed: {doc_type}",
              {"document_type": doc_type})

def log_facts_extracted(claim_id: str, fact_count: int):
    log_event(claim_id, "FACTS_EXTRACTED", f"Extracted {fact_count} facts",
              {"fact_count": fact_count})

def log_policy_retrieved(claim_id: str, clause_count: int):
    log_event(claim_id, "POLICY_RETRIEVED", f"Retrieved {clause_count} policy clauses",
              {"clause_count": clause_count})

def log_evidence_matched(claim_id: str):
    log_event(claim_id, "EVIDENCE_MATCHED", "Evidence matching completed")

def log_contradiction_found(claim_id: str, field: str, severity: str):
    log_event(claim_id, "CONTRADICTION_FOUND", f"Contradiction in {field} ({severity})",
              {"field": field, "severity": severity})

def log_recommendation_generated(claim_id: str, recommendation: str, confidence: str):
    log_event(claim_id, "RECOMMENDATION_GENERATED",
              f"Recommendation: {recommendation} (Confidence: {confidence})",
              {"recommendation": recommendation, "confidence": confidence})

def log_escalation(claim_id: str, reason: str):
    log_event(claim_id, "ESCALATION", f"Claim escalated: {reason}", {"reason": reason})

def log_simulation(claim_id: str, params: dict, result: str):
    log_event(claim_id, "SIMULATION", f"Simulation run — result: {result}",
              {"parameters": params, "result": result})

def log_review_updated(claim_id: str, version: int):
    log_event(claim_id, "REVIEW_UPDATED", f"Review updated to version {version}",
              {"version": version})

def get_claim_audit_trail(claim_id: str) -> list:
    return get_audit_trail(claim_id)

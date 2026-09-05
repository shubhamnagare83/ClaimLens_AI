"""
ClaimLens AI — Policy Engine
Deterministic policy evaluation against extracted facts.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from backend.config import POLICY_DIR
from backend.services import retrieval_service

_policy_data = None
_coverage_rules = None
_required_docs = None
_exclusions = None


def init_policy():
    """Load all policy data."""
    global _policy_data, _coverage_rules, _required_docs, _exclusions

    try:
        with open(POLICY_DIR / "motor_policy.json", 'r') as f:
            _policy_data = json.load(f)
        with open(POLICY_DIR / "coverage_rules.json", 'r') as f:
            _coverage_rules = json.load(f)
        with open(POLICY_DIR / "required_documents.json", 'r') as f:
            _required_docs = json.load(f)
        with open(POLICY_DIR / "exclusions.json", 'r') as f:
            _exclusions = json.load(f)
        print("  [OK] Policy data loaded")
        return True
    except Exception as e:
        print(f"  [!] Error loading policy: {e}")
        return False


def get_required_documents(incident_type: str) -> Dict:
    """Get required documents for a claim type."""
    if not _required_docs:
        return {"mandatory": [], "conditional": {}}
    it = incident_type.lower()
    return _required_docs.get(it, {"mandatory": [], "conditional": {}})


def get_applicable_clauses(incident_type: str) -> List[str]:
    """Get applicable clause IDs for an incident type."""
    if not _coverage_rules:
        return []
    it = incident_type.lower()
    if it in _coverage_rules:
        sub = list(_coverage_rules[it].values())[0] if _coverage_rules[it] else {}
        return sub.get('applicable_clauses', [])
    return []


def get_exclusions() -> List[Dict]:
    """Get all exclusion rules."""
    if not _exclusions:
        return []
    return _exclusions.get('exclusions', [])


def get_clause_details(clause_id: str) -> Optional[Dict]:
    """Get full details for a clause."""
    if not _policy_data:
        return None
    for clause in _policy_data.get('clauses', []):
        if clause['clause_id'] == clause_id:
            return clause
    return None


def get_all_policy_clauses() -> List[Dict]:
    """Get all policy clauses."""
    if not _policy_data:
        return []
    return _policy_data.get('clauses', [])


def evaluate_claim_against_policy(claim: Dict, documents: Dict[str, str],
                                   extracted_facts: Dict) -> List[Dict]:
    """
    Evaluate a claim against all relevant policy clauses.
    Returns list of policy findings.
    """
    findings = []
    incident_type = claim.get('incident_type', 'Accident')

    # Get relevant clauses
    relevant_clause_ids = get_applicable_clauses(incident_type)
    # Always check core clauses
    core_clauses = ['POL-001', 'POL-005', 'POL-006', 'POL-014', 'POL-015', 'POL-033', 'POL-034']
    all_clause_ids = list(set(relevant_clause_ids + core_clauses))

    for clause_id in sorted(all_clause_ids):
        clause = get_clause_details(clause_id)
        if not clause:
            continue

        finding = _evaluate_clause(clause, claim, documents, extracted_facts)
        findings.append(finding)

    return findings


def _evaluate_clause(clause: Dict, claim: Dict, documents: Dict[str, str],
                     facts: Dict) -> Dict:
    """Evaluate a single clause. Returns a finding dict."""
    clause_id = clause['clause_id']
    result = {
        'clause_id': clause_id,
        'title': clause['title'],
        'category': clause['category'],
        'rule': clause['rule'],
        'status': 'PASS',
        'evidence': '',
        'source_document': '',
        'calculation': '',
        'confidence': 'HIGH',
    }

    # Dispatch to specific evaluators
    evaluators = {
        'POL-001': _eval_policy_validity,
        'POL-005': _eval_claim_window,
        'POL-006': _eval_required_documents,
        'POL-014': _eval_idv,
        'POL-015': _eval_deductible,
        'POL-016': _eval_theft_fir,
        'POL-017': _eval_theft_keys,
        'POL-026': _eval_total_loss,
    }

    evaluator = evaluators.get(clause_id)
    if evaluator:
        result = evaluator(clause, claim, documents, facts, result)

    return result


def _eval_policy_validity(clause, claim, docs, facts, result):
    """POL-001: Check if incident is within policy period."""
    from backend.services.calculation_engine import parse_date
    incident_date = parse_date(claim.get('incident_date', ''))
    policy_start = parse_date(claim.get('policy_start_date', ''))
    policy_end = parse_date(claim.get('policy_end_date', ''))

    if incident_date and policy_start and policy_end:
        if policy_start <= incident_date <= policy_end:
            result['status'] = 'PASS'
            result['evidence'] = f"Incident date {claim['incident_date']} is within policy period {claim['policy_start_date']} to {claim['policy_end_date']}"
            result['calculation'] = f"Policy: {claim['policy_start_date']} to {claim['policy_end_date']}, Incident: {claim['incident_date']}"
        else:
            result['status'] = 'FAIL'
            result['evidence'] = f"Incident date {claim['incident_date']} is OUTSIDE policy period {claim['policy_start_date']} to {claim['policy_end_date']}"
            result['calculation'] = f"Policy expired or not yet active"
            result['confidence'] = 'HIGH'
    else:
        result['status'] = 'UNKNOWN'
        result['evidence'] = 'Unable to determine policy validity — missing dates'
        result['confidence'] = 'LOW'

    return result


def _eval_claim_window(clause, claim, docs, facts, result):
    """POL-005: Check claim notification window (7 days)."""
    from backend.services.calculation_engine import calculate_days_between, parse_date
    incident_date = claim.get('incident_date', '')
    claim_date = claim.get('claim_date', '')

    days = calculate_days_between(incident_date, claim_date)
    if days is not None:
        result['calculation'] = f"Claim date ({claim_date}) - Incident date ({incident_date}) = {days} days"
        if days <= 7:
            result['status'] = 'PASS'
            result['evidence'] = f"Claim filed within {days} days (within 7-day window)"
        elif days <= 14:
            result['status'] = 'WARNING'
            result['evidence'] = f"Claim filed after {days} days (beyond 7-day window, reasonable delay may apply)"
            result['confidence'] = 'MEDIUM'
        else:
            result['status'] = 'FAIL'
            result['evidence'] = f"Claim filed after {days} days (significantly beyond 7-day window)"
            result['confidence'] = 'HIGH'
    else:
        result['status'] = 'UNKNOWN'
        result['evidence'] = 'Unable to calculate claim window — missing dates'
        result['confidence'] = 'LOW'

    return result


def _eval_required_documents(clause, claim, docs, facts, result):
    """POL-006: Check required documents."""
    incident_type = claim.get('incident_type', 'Accident')
    required = get_required_documents(incident_type)
    mandatory = required.get('mandatory', [])

    doc_types = set(docs.keys()) if docs else set()
    missing = [d for d in mandatory if d not in doc_types]

    if not missing:
        result['status'] = 'PASS'
        result['evidence'] = f"All mandatory documents present: {', '.join(mandatory)}"
    else:
        result['status'] = 'FAIL'
        result['evidence'] = f"Missing mandatory documents: {', '.join(missing)}"
        result['confidence'] = 'HIGH'

    return result


def _eval_idv(clause, claim, docs, facts, result):
    """POL-014: Check repair estimate against IDV."""
    idv = claim.get('idv', 0)
    repair = claim.get('repair_estimate', 0)

    if idv > 0 and repair > 0:
        result['calculation'] = f"Repair estimate: Rs. {repair:,.0f}, IDV: Rs. {idv:,.0f}"
        if repair <= idv:
            result['status'] = 'PASS'
            result['evidence'] = f"Repair estimate (Rs. {repair:,.0f}) is within IDV (Rs. {idv:,.0f})"
        else:
            result['status'] = 'WARNING'
            result['evidence'] = f"Repair estimate (Rs. {repair:,.0f}) exceeds IDV (Rs. {idv:,.0f}). Claim limited to IDV."
            result['confidence'] = 'HIGH'
    else:
        result['status'] = 'UNKNOWN'
        result['evidence'] = 'IDV or repair estimate not available'
        result['confidence'] = 'LOW'

    return result


def _eval_deductible(clause, claim, docs, facts, result):
    """POL-015: Apply deductible."""
    vehicle_type = claim.get('vehicle_type', 'Car')
    deductible = claim.get('deductible', 0)
    expected = 2000 if vehicle_type == 'Car' else 1000

    result['calculation'] = f"Vehicle type: {vehicle_type}, Compulsory deductible: Rs. {expected:,}"
    result['status'] = 'PASS'
    result['evidence'] = f"Deductible of Rs. {expected:,} applicable for {vehicle_type}"
    return result


def _eval_theft_fir(clause, claim, docs, facts, result):
    """POL-016: FIR requirement for theft claims."""
    if claim.get('incident_type', '') != 'Theft':
        result['status'] = 'PASS'
        result['evidence'] = 'Not a theft claim — FIR requirement not applicable'
        return result

    doc_types = set(docs.keys()) if docs else set()
    if 'fir' in doc_types:
        result['status'] = 'PASS'
        result['evidence'] = 'FIR document is present for theft claim'
    else:
        result['status'] = 'FAIL'
        result['evidence'] = 'FIR is MISSING for theft claim — mandatory requirement'
        result['confidence'] = 'HIGH'

    return result


def _eval_theft_keys(clause, claim, docs, facts, result):
    """POL-017: Key declaration requirement for theft claims."""
    if claim.get('incident_type', '') != 'Theft':
        result['status'] = 'PASS'
        result['evidence'] = 'Not a theft claim — key requirement not applicable'
        return result

    doc_types = set(docs.keys()) if docs else set()
    if 'key_declaration' in doc_types:
        # Check if keys are accounted for
        keys_facts = facts.get('keys_status', [])
        keys_missing = any(f.get('value') == 'keys_missing' for f in keys_facts)
        if keys_missing:
            result['status'] = 'WARNING'
            result['evidence'] = 'Key declaration present but some keys are unaccounted for'
            result['confidence'] = 'MEDIUM'
        else:
            result['status'] = 'PASS'
            result['evidence'] = 'Key declaration present and keys accounted for'
    else:
        result['status'] = 'FAIL'
        result['evidence'] = 'Key declaration is MISSING for theft claim — required document'
        result['confidence'] = 'HIGH'

    return result


def _eval_total_loss(clause, claim, docs, facts, result):
    """POL-026: Total loss assessment."""
    idv = claim.get('idv', 0)
    repair = claim.get('repair_estimate', 0)

    if idv > 0 and repair > 0:
        ratio = repair / idv * 100
        result['calculation'] = f"Repair/IDV ratio: {ratio:.1f}% (threshold: 75%)"
        if ratio >= 75:
            result['status'] = 'WARNING'
            result['evidence'] = f"Repair estimate ({ratio:.1f}% of IDV) may qualify as total loss"
        else:
            result['status'] = 'PASS'
            result['evidence'] = f"Repair estimate ({ratio:.1f}% of IDV) is within partial loss range"

    return result

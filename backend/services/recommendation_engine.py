"""
ClaimLens AI — Recommendation Engine
Deterministic decision logic. Priority: ESCALATE > REJECT > REQUEST_INFORMATION > APPROVE.
"""
from typing import Dict, List


def generate_recommendation(policy_findings: List[Dict],
                           consistency_checks: List[Dict],
                           completeness: Dict,
                           exclusion_indicators: List[Dict],
                           calculations: Dict) -> Dict:
    """
    Generate final recommendation based on all evidence.
    Returns recommendation dict with explanation.
    """
    reasons = []
    blocking = []
    warnings = []
    missing = []
    contradictions = []

    # 1. Check for CRITICAL/HIGH contradictions → ESCALATE
    for check in consistency_checks:
        if check.get('status') == 'CONTRADICTION':
            severity = check.get('severity', 'LOW')
            contradictions.append(check)
            if severity in ('CRITICAL', 'HIGH'):
                reasons.append(f"Critical contradiction in {check['field_name']}: {check.get('details', '')}")

    # 2. Check policy findings for FAIL → potential REJECT
    for finding in policy_findings:
        if finding.get('status') == 'FAIL':
            clause = finding.get('clause_id', '')
            # Policy validity failure is a hard REJECT
            if clause == 'POL-001':
                blocking.append(f"Policy not active at time of incident [{clause}]")
            elif clause in ('POL-009', 'POL-010', 'POL-011', 'POL-012', 'POL-013'):
                # Exclusion-related failures
                blocking.append(f"{finding['title']}: {finding['evidence']} [{clause}]")
            elif clause in ('POL-006', 'POL-016', 'POL-017', 'POL-018'):
                # Document-related failures → REQUEST_INFORMATION
                missing.append(f"{finding['title']}: {finding['evidence']} [{clause}]")
            else:
                warnings.append(f"{finding['title']}: {finding['evidence']} [{clause}]")
        elif finding.get('status') == 'WARNING':
            warnings.append(f"{finding['title']}: {finding['evidence']} [{finding.get('clause_id', '')}]")

    # 3. Check exclusion indicators
    for exc in exclusion_indicators:
        if exc.get('confidence', 0) >= 0.7:
            blocking.append(f"Exclusion indicator: {exc.get('type', '').replace('_', ' ')} — {exc.get('evidence', '')}")

    # 4. Check completeness
    if not completeness.get('is_complete', True):
        for doc in completeness.get('missing_documents', []):
            missing.append(f"Missing: {doc['label']} (required by {', '.join(doc.get('required_by', []))})")

    # ── Decision Logic ──
    # Priority: ESCALATE > REJECT > REQUEST_INFORMATION > APPROVE

    has_critical_contradictions = len(contradictions) > 0 and any(
        c.get('severity') in ('CRITICAL', 'HIGH') for c in contradictions
    )

    if has_critical_contradictions:
        recommendation = 'ESCALATE'
        confidence = 'HIGH'
        explanation = _build_explanation('ESCALATE', reasons, blocking, missing, warnings, contradictions)
    elif blocking:
        recommendation = 'REJECT'
        confidence = 'HIGH'
        explanation = _build_explanation('REJECT', reasons, blocking, missing, warnings, contradictions)
    elif missing:
        recommendation = 'REQUEST_INFORMATION'
        confidence = 'MEDIUM'
        explanation = _build_explanation('REQUEST_INFORMATION', reasons, blocking, missing, warnings, contradictions)
    elif warnings:
        # Warnings alone don't block, but lower confidence
        recommendation = 'APPROVE'
        confidence = 'MEDIUM'
        explanation = _build_explanation('APPROVE', reasons, blocking, missing, warnings, contradictions)
    else:
        recommendation = 'APPROVE'
        confidence = 'HIGH'
        explanation = _build_explanation('APPROVE', reasons, blocking, missing, warnings, contradictions)

    # Calculate evidence score
    evidence_score = _calculate_evidence_score(
        policy_findings, consistency_checks, completeness, exclusion_indicators
    )

    return {
        'recommendation': recommendation,
        'confidence': confidence,
        'human_review_required': recommendation != 'APPROVE' or confidence != 'HIGH',
        'evidence_score': evidence_score['total'],
        'evidence_score_breakdown': evidence_score['breakdown'],
        'explanation': explanation,
        'reasons': reasons,
        'blocking_conditions': blocking,
        'missing_information': missing,
        'warnings': warnings,
        'contradiction_count': len(contradictions),
        'disclaimer': 'This recommendation is decision support. Final claim determination remains with an authorized human investigator.',
    }


def _build_explanation(rec: str, reasons: list, blocking: list,
                       missing: list, warnings: list, contradictions: list) -> str:
    """Build human-readable explanation."""
    parts = []

    if rec == 'APPROVE':
        parts.append("Based on the available evidence, the claim meets policy requirements.")
        if warnings:
            parts.append(f"\nNote: {len(warnings)} warning(s) identified but not blocking:")
            for w in warnings:
                parts.append(f"  - {w}")
    elif rec == 'REJECT':
        parts.append("The claim cannot be approved due to policy exclusions or blocking conditions:")
        for b in blocking:
            parts.append(f"  - {b}")
    elif rec == 'REQUEST_INFORMATION':
        parts.append("Additional information is required to process this claim:")
        for m in missing:
            parts.append(f"  - {m}")
    elif rec == 'ESCALATE':
        parts.append("This claim requires human investigator review due to:")
        if contradictions:
            parts.append(f"  - {len(contradictions)} contradiction(s) found across documents")
            for c in contradictions:
                parts.append(f"    * {c.get('field_name', '')}: {c.get('details', '')}")
        for r in reasons:
            parts.append(f"  - {r}")

    return "\n".join(parts)


def _calculate_evidence_score(policy_findings, consistency_checks,
                               completeness, exclusion_indicators) -> Dict:
    """Calculate evidence consistency score (0-100)."""
    breakdown = {}

    # Document completeness (25%)
    comp_score = completeness.get('completeness_score', 0)
    breakdown['document_completeness'] = round(comp_score, 1)

    # Cross-document consistency (30%)
    if consistency_checks:
        matches = sum(1 for c in consistency_checks if c.get('status') == 'MATCH')
        partials = sum(1 for c in consistency_checks if c.get('status') == 'PARTIAL_MATCH')
        total_checks = len(consistency_checks)
        if total_checks > 0:
            consistency_score = ((matches + partials * 0.7) / total_checks) * 100
        else:
            consistency_score = 100
    else:
        consistency_score = 50  # Unknown
    breakdown['cross_document_consistency'] = round(consistency_score, 1)

    # Policy compliance (25%)
    if policy_findings:
        passes = sum(1 for f in policy_findings if f.get('status') == 'PASS')
        total_findings = len(policy_findings)
        policy_score = (passes / max(total_findings, 1)) * 100
    else:
        policy_score = 50
    breakdown['policy_compliance'] = round(policy_score, 1)

    # No exclusions (20%)
    if not exclusion_indicators:
        exclusion_score = 100
    else:
        exclusion_score = max(0, 100 - len(exclusion_indicators) * 30)
    breakdown['no_exclusions'] = round(exclusion_score, 1)

    # Weighted total
    total = (comp_score * 0.25 + consistency_score * 0.30 +
             policy_score * 0.25 + exclusion_score * 0.20)

    return {
        'total': round(total, 1),
        'breakdown': breakdown,
    }


def generate_what_would_change(recommendation: str, missing_info: list,
                                contradictions: list, blocking: list) -> List[Dict]:
    """Generate 'what would change the decision' scenarios."""
    scenarios = []

    if recommendation == 'REQUEST_INFORMATION':
        for item in missing_info:
            scenarios.append({
                'current_issue': item,
                'if_resolved': 'If this document is provided and verified',
                'potential_outcome': 'Could move toward APPROVE if no other issues exist',
            })

    elif recommendation == 'ESCALATE':
        for c in contradictions:
            field = c.get('field_name', 'Unknown')
            scenarios.append({
                'current_issue': f"Contradiction in {field}",
                'if_resolved': f"If the correct {field} is confirmed with supporting evidence",
                'potential_outcome': 'Could be resolved — claim window and other calculations can be verified',
            })

    elif recommendation == 'REJECT':
        for b in blocking:
            scenarios.append({
                'current_issue': b,
                'if_resolved': 'This is a policy exclusion — typically cannot be overridden',
                'potential_outcome': 'REJECT unless exclusion is found to be inapplicable',
            })

    return scenarios


def generate_handoff(claim: Dict, recommendation: str, contradictions: list,
                     missing_info: list, policy_findings: list) -> Dict:
    """Generate investigator handoff document."""
    if recommendation in ('APPROVE',):
        return None

    handoff = {
        'claim_id': claim.get('claim_id', ''),
        'recommendation': recommendation,
        'priority': 'HIGH' if recommendation == 'ESCALATE' else 'MEDIUM',
        'issues': [],
        'already_verified': [],
        'next_steps': [],
    }

    # Issues
    for c in contradictions:
        if c.get('status') == 'CONTRADICTION':
            handoff['issues'].append({
                'type': 'Contradiction',
                'field': c.get('field_name', ''),
                'details': c.get('details', ''),
                'values': c.get('values', {}),
            })

    for m in missing_info:
        handoff['issues'].append({'type': 'Missing Document', 'details': m})

    # Already verified
    for f in policy_findings:
        if f.get('status') == 'PASS':
            handoff['already_verified'].append(f"{f.get('title', '')} [{f.get('clause_id', '')}]")

    # Next steps
    if contradictions:
        handoff['next_steps'].append('Obtain supporting evidence to resolve contradictions')
    if missing_info:
        handoff['next_steps'].append('Request missing documents from policyholder')
    handoff['next_steps'].append('Complete independent assessment')

    return handoff

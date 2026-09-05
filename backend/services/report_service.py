"""
ClaimLens AI — Report Service
Orchestrates the full claim review pipeline and assembles the final report.
"""
import json
from typing import Dict, List, Optional
from backend.services import (
    extraction_service, consistency_engine, completeness_engine,
    calculation_engine, policy_engine, recommendation_engine,
    citation_service, audit_service, retrieval_service, gemini_service
)
from backend.database import (
    get_claim, get_claim_documents, insert_review, get_latest_review,
    get_review_versions, insert_finding, insert_extracted_fact
)


def run_full_review(claim_id: str) -> Dict:
    """
    Run the complete review pipeline for a claim.
    Returns the full report.
    """
    # 1. Load claim data
    claim = get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    audit_service.log_event(claim_id, "REVIEW_STARTED", "AI review initiated")

    # 2. Load documents
    doc_rows = get_claim_documents(claim_id)
    documents = {}
    for doc in doc_rows:
        doc_type = doc['document_type']
        documents[doc_type] = doc['content']
        audit_service.log_document_parsed(claim_id, doc_type)

    # 3. Extract facts
    extracted_facts = extraction_service.extract_facts_from_documents(claim_id, documents)
    total_facts = sum(len(v) for v in extracted_facts.values())
    audit_service.log_facts_extracted(claim_id, total_facts)

    # Save extracted facts to database
    for field_name, facts_list in extracted_facts.items():
        for fact in facts_list:
            try:
                insert_extracted_fact(
                    claim_id, field_name, str(fact.get('value', '')),
                    fact.get('source_document', ''), fact.get('evidence', ''),
                    fact.get('confidence', 0)
                )
            except:
                pass

    # 4. Check consistency
    consistency_checks = consistency_engine.check_consistency(extracted_facts)
    for check in consistency_checks:
        if check.get('status') == 'CONTRADICTION':
            audit_service.log_contradiction_found(
                claim_id, check.get('field_name', ''), check.get('severity', 'LOW')
            )

    # 5. Check completeness
    completeness = completeness_engine.check_completeness(claim, documents)

    # 6. Detect exclusions
    exclusion_indicators = consistency_engine.detect_exclusion_indicators(documents)

    # 7. Run calculations
    calculations = {
        'claim_window': calculation_engine.check_claim_window(
            claim.get('incident_date', ''), claim.get('claim_date', '')),
        'policy_validity': calculation_engine.check_policy_validity(
            claim.get('incident_date', ''), claim.get('policy_start_date', ''),
            claim.get('policy_end_date', '')),
        'idv_check': calculation_engine.check_idv_limit(
            claim.get('repair_estimate', 0), claim.get('idv', 0)),
        'total_loss': calculation_engine.check_total_loss(
            claim.get('repair_estimate', 0), claim.get('idv', 0)),
        'deductible': calculation_engine.calculate_deductible(claim.get('vehicle_type', 'Car')),
        'net_claim': calculation_engine.calculate_net_claim(
            claim.get('repair_estimate', 0), claim.get('deductible', 0),
            claim.get('idv', 0)),
    }

    # 8. Evaluate against policy
    policy_findings = policy_engine.evaluate_claim_against_policy(
        claim, documents, extracted_facts)
    audit_service.log_policy_retrieved(claim_id, len(policy_findings))
    audit_service.log_evidence_matched(claim_id)

    # 9. Generate recommendation
    rec_result = recommendation_engine.generate_recommendation(
        policy_findings, consistency_checks, completeness,
        exclusion_indicators, calculations
    )
    audit_service.log_recommendation_generated(
        claim_id, rec_result['recommendation'], rec_result['confidence'])

    if rec_result['recommendation'] == 'ESCALATE':
        audit_service.log_escalation(claim_id, rec_result.get('explanation', ''))

    # 10. Generate citations
    citations = citation_service.generate_citations_from_findings(policy_findings)
    citations.extend(citation_service.generate_citations_from_facts(extracted_facts))

    # 11. Build timeline
    timeline = calculation_engine.build_timeline(claim)

    # 12. Generate what-would-change
    contradictions = [c for c in consistency_checks if c.get('status') == 'CONTRADICTION']
    what_would_change = recommendation_engine.generate_what_would_change(
        rec_result['recommendation'],
        rec_result.get('missing_information', []),
        contradictions,
        rec_result.get('blocking_conditions', [])
    )

    # 13. Generate handoff
    handoff = recommendation_engine.generate_handoff(
        claim, rec_result['recommendation'], contradictions,
        rec_result.get('missing_information', []), policy_findings
    )

    # 14. Build evidence matrix
    evidence_matrix = _build_evidence_matrix(
        claim, documents, policy_findings, completeness)

    # 15. Generate explanation using Gemini if available
    explanation = rec_result.get('explanation', '')
    if gemini_service.is_available():
        ai_explanation = _generate_ai_explanation(claim, rec_result, policy_findings,
                                                   consistency_checks, completeness)
        if ai_explanation:
            explanation = ai_explanation

    # 16. Assemble report
    report = {
        'claim_id': claim_id,
        'recommendation': rec_result['recommendation'],
        'human_review_required': rec_result['human_review_required'],
        'confidence': rec_result['confidence'],
        'evidence_score': rec_result['evidence_score'],
        'evidence_score_breakdown': rec_result.get('evidence_score_breakdown', {}),
        'documents': {k: {'type': k, 'present': True, 'length': len(v)} for k, v in documents.items()},
        'facts': extracted_facts,
        'policy_findings': [f for f in policy_findings],
        'contradictions': [c for c in consistency_checks if c.get('status') == 'CONTRADICTION'],
        'consistency_checks': consistency_checks,
        'missing_information': completeness.get('missing_documents', []),
        'completeness': completeness,
        'exclusion_indicators': exclusion_indicators,
        'calculations': calculations,
        'citations': citations,
        'timeline': timeline,
        'evidence_matrix': evidence_matrix,
        'handoff': handoff,
        'what_would_change': what_would_change,
        'explanation': explanation,
        'disclaimer': rec_result.get('disclaimer', ''),
    }

    # 17. Save review
    existing = get_latest_review(claim_id)
    version = (existing['version'] + 1) if existing else 1
    review_id = insert_review(
        claim_id, version, rec_result['recommendation'],
        rec_result['confidence'], rec_result['evidence_score'], report
    )
    audit_service.log_review_updated(claim_id, version)

    # Save findings
    for finding in policy_findings:
        try:
            insert_finding(
                review_id, claim_id, 'policy', finding.get('status', 'UNKNOWN'),
                finding.get('title', ''), finding.get('evidence', ''),
                finding.get('clause_id', ''), finding.get('source_document', ''),
                1, finding.get('evidence', ''), finding.get('confidence', 'LOW')
            )
        except:
            pass

    for contradiction in contradictions:
        try:
            insert_finding(
                review_id, claim_id, 'contradiction', contradiction.get('severity', 'LOW'),
                f"Contradiction: {contradiction.get('field_name', '')}",
                contradiction.get('details', ''), '', '', 1,
                json.dumps(contradiction.get('values', {})),
                'HIGH'
            )
        except:
            pass

    report['version'] = version
    return report


def _build_evidence_matrix(claim, documents, policy_findings, completeness) -> List[Dict]:
    """Build the evidence matrix."""
    matrix = []
    incident_type = claim.get('incident_type', 'Accident')

    # Required documents
    reqs = policy_engine.get_required_documents(incident_type)
    mandatory = reqs.get('mandatory', [])

    doc_labels = {
        'claim_form': 'Claim Form', 'incident_description': 'Incident Description',
        'repair_estimate': 'Repair Estimate', 'fir': 'FIR',
        'vehicle_rc': 'Vehicle RC', 'key_declaration': 'Key Declaration',
        'driving_license': 'Driving Licence',
    }

    for doc in mandatory:
        present = doc in documents
        label = doc_labels.get(doc, doc)
        clause = _doc_to_clause(doc, incident_type)
        matrix.append({
            'requirement': f'{label} required',
            'policy_clause': clause,
            'evidence': f'{label} {"uploaded" if present else "NOT uploaded"}',
            'source': f'{doc}.txt' if present else 'Missing',
            'status': 'PASS' if present else 'FAIL',
            'confidence': 'HIGH',
        })

    # Policy validity
    for f in policy_findings:
        if f.get('clause_id') in ('POL-001', 'POL-005', 'POL-014'):
            matrix.append({
                'requirement': f.get('title', ''),
                'policy_clause': f.get('clause_id', ''),
                'evidence': f.get('evidence', ''),
                'source': f.get('source_document', 'Claim Data'),
                'status': f.get('status', 'UNKNOWN'),
                'confidence': f.get('confidence', 'LOW'),
            })

    return matrix


def _doc_to_clause(doc_type: str, incident_type: str) -> str:
    mapping = {
        'claim_form': 'POL-006',
        'incident_description': 'POL-023',
        'repair_estimate': 'POL-018',
        'fir': 'POL-016' if incident_type == 'Theft' else 'POL-025',
        'vehicle_rc': 'POL-007',
        'key_declaration': 'POL-017',
        'driving_license': 'POL-008',
    }
    return mapping.get(doc_type, 'POL-006')


def _generate_ai_explanation(claim, rec_result, policy_findings,
                              consistency_checks, completeness) -> Optional[str]:
    """Use Gemini to generate a human-readable explanation."""
    prompt = f"""Summarize this insurance claim review in 3-4 clear sentences for a human investigator.

Claim: {claim.get('claim_id', '')} — {claim.get('incident_type', '')} — {claim.get('vehicle_type', '')}
Recommendation: {rec_result['recommendation']}
Confidence: {rec_result['confidence']}
Evidence Score: {rec_result['evidence_score']}/100

Key findings:
- Policy findings: {len(policy_findings)} checks, {sum(1 for f in policy_findings if f.get('status')=='PASS')} passed
- Contradictions: {sum(1 for c in consistency_checks if c.get('status')=='CONTRADICTION')}
- Documents complete: {'Yes' if completeness.get('is_complete') else 'No'}
- Blocking conditions: {len(rec_result.get('blocking_conditions', []))}

Write a clear, professional summary. Do not mention fraud. This is decision support only."""

    return gemini_service.generate_text(prompt, "Provide a brief professional summary. No speculation.")

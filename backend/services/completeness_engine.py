"""
ClaimLens AI — Completeness Engine
Checks document completeness based on claim type and policy requirements.
"""
from typing import Dict, List
from backend.services.policy_engine import get_required_documents


def check_completeness(claim: Dict, documents: Dict[str, str]) -> Dict:
    """
    Check if all required documents are present.
    Returns completeness report.
    """
    incident_type = claim.get('incident_type', 'Accident')
    required = get_required_documents(incident_type)
    mandatory = required.get('mandatory', [])
    conditional = required.get('conditional', {})

    doc_types = set(documents.keys()) if documents else set()

    present = [d for d in mandatory if d in doc_types]
    missing = [d for d in mandatory if d not in doc_types]

    # Build report
    doc_status = {}
    for doc in mandatory:
        doc_status[doc] = {
            'required': True,
            'present': doc in doc_types,
            'label': _doc_label(doc),
        }
    for doc, reason in conditional.items():
        doc_status[doc] = {
            'required': False,
            'present': doc in doc_types,
            'label': _doc_label(doc),
            'condition': reason,
        }

    completeness_score = len(present) / max(len(mandatory), 1) * 100

    return {
        'is_complete': len(missing) == 0,
        'completeness_score': round(completeness_score, 1),
        'mandatory_count': len(mandatory),
        'present_count': len(present),
        'missing_count': len(missing),
        'missing_documents': [
            {
                'document_type': d,
                'label': _doc_label(d),
                'required_by': _required_by_clauses(d, incident_type),
                'impact': _missing_impact(d, incident_type),
            }
            for d in missing
        ],
        'document_status': doc_status,
    }


def _doc_label(doc_type: str) -> str:
    labels = {
        'claim_form': 'Claim Form',
        'incident_description': 'Incident Description',
        'repair_estimate': 'Repair Estimate',
        'fir': 'First Information Report (FIR)',
        'vehicle_rc': 'Vehicle Registration Certificate (RC)',
        'driving_license': 'Driving Licence',
        'key_declaration': 'Key Declaration',
        'repair_invoice': 'Repair Invoice',
    }
    return labels.get(doc_type, doc_type.replace('_', ' ').title())


def _required_by_clauses(doc_type: str, incident_type: str) -> List[str]:
    clause_map = {
        'claim_form': ['POL-006'],
        'incident_description': ['POL-006', 'POL-023'],
        'repair_estimate': ['POL-006', 'POL-018'],
        'fir': ['POL-016'] if incident_type == 'Theft' else ['POL-025'],
        'vehicle_rc': ['POL-007', 'POL-020'],
        'driving_license': ['POL-008'],
        'key_declaration': ['POL-017'],
        'repair_invoice': ['POL-019'],
    }
    return clause_map.get(doc_type, ['POL-006'])


def _missing_impact(doc_type: str, incident_type: str) -> str:
    impacts = {
        'claim_form': 'Claim cannot be processed without the claim form.',
        'incident_description': 'Incident details cannot be verified without the description.',
        'repair_estimate': 'Damage assessment and claim amount cannot be determined.',
        'fir': 'Police report is mandatory for theft claims.' if incident_type == 'Theft' else 'Police report may be required for third-party incidents.',
        'vehicle_rc': 'Vehicle ownership and registration cannot be verified.',
        'driving_license': 'Driver validity at the time of incident cannot be confirmed.',
        'key_declaration': 'Vehicle key accountability cannot be verified for theft claim.',
        'repair_invoice': 'Final settlement amount cannot be determined without invoice.',
    }
    return impacts.get(doc_type, 'Required document missing — claim processing delayed.')

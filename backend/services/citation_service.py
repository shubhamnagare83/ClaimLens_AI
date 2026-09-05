"""
ClaimLens AI — Citation Service
Attaches source references to every finding.
"""
from typing import Dict, List


def create_citation(source_document: str, page: int, evidence_snippet: str,
                    policy_clause: str = '') -> Dict:
    """Create a citation reference."""
    return {
        'source_document': source_document,
        'page': page,
        'evidence_snippet': evidence_snippet,
        'policy_clause': policy_clause,
        'reference': _format_reference(source_document, page, policy_clause),
    }


def _format_reference(source_doc: str, page: int, clause: str) -> str:
    parts = []
    if source_doc:
        parts.append(f"{source_doc} - Page {page}")
    if clause:
        parts.append(f"[{clause}]")
    return " | ".join(parts) if parts else "No reference"


def generate_citations_from_facts(facts: Dict[str, list]) -> List[Dict]:
    """Generate citations from extracted facts."""
    citations = []
    for field_name, fact_list in facts.items():
        for fact in fact_list:
            citations.append(create_citation(
                source_document=fact.get('source_document', ''),
                page=1,
                evidence_snippet=fact.get('evidence', ''),
                policy_clause='',
            ))
    return citations


def generate_citations_from_findings(policy_findings: List[Dict]) -> List[Dict]:
    """Generate citations from policy findings."""
    citations = []
    for finding in policy_findings:
        if finding.get('evidence'):
            citations.append(create_citation(
                source_document=finding.get('source_document', ''),
                page=1,
                evidence_snippet=finding.get('evidence', ''),
                policy_clause=finding.get('clause_id', ''),
            ))
    return citations

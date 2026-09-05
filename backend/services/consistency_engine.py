"""
ClaimLens AI — Consistency Engine
Cross-document fact comparison to detect contradictions.
"""
from typing import Dict, List, Optional
from backend.services import gemini_service


def check_consistency(extracted_facts: Dict[str, list]) -> List[Dict]:
    """
    Compare extracted facts across documents.
    Returns list of consistency checks.
    """
    checks = []

    # Fields to check for cross-document consistency
    fields_to_check = [
        ('vehicle_registration', 'CRITICAL', 'Vehicle Registration'),
        ('incident_date', 'HIGH', 'Incident Date'),
        ('incident_time', 'MEDIUM', 'Incident Time'),
        ('incident_location', 'MEDIUM', 'Incident Location'),
        ('customer_name', 'HIGH', 'Customer Name'),
    ]

    for field_name, default_severity, display_name in fields_to_check:
        facts = extracted_facts.get(field_name, [])
        if len(facts) < 2:
            if facts:
                checks.append({
                    'field_name': display_name,
                    'status': 'MATCH',
                    'severity': 'LOW',
                    'values': {facts[0].get('source_document', 'unknown'): facts[0].get('value', '')},
                    'details': f'{display_name} found in one document only',
                })
            continue

        # Get unique values
        values = {}
        for fact in facts:
            src = fact.get('source_document', 'unknown')
            val = fact.get('value', '').strip()
            if val:
                values[src] = val

        unique_values = set(values.values())

        if len(unique_values) == 1:
            checks.append({
                'field_name': display_name,
                'status': 'MATCH',
                'severity': 'LOW',
                'values': values,
                'details': f'{display_name} is consistent across all documents',
            })
        elif _is_partial_match(field_name, unique_values):
            checks.append({
                'field_name': display_name,
                'status': 'PARTIAL_MATCH',
                'severity': 'LOW' if field_name in ('incident_time',) else 'MEDIUM',
                'values': values,
                'details': f'{display_name} has minor variations across documents — may be formatting differences',
            })
        else:
            impact = _get_contradiction_impact(field_name)
            checks.append({
                'field_name': display_name,
                'status': 'CONTRADICTION',
                'severity': default_severity,
                'values': values,
                'details': f'CONTRADICTION: {display_name} differs across documents',
                'impact': impact,
                'action': 'Investigator review required',
            })

    return checks


def _is_partial_match(field_name: str, values: set) -> bool:
    """Check if value differences are just formatting variations."""
    if field_name == 'incident_date':
        return _dates_match(values)
    if field_name == 'incident_time':
        return _times_close(values)
    if field_name == 'incident_location':
        # Check if locations share significant words
        value_list = list(values)
        if len(value_list) == 2:
            words1 = set(value_list[0].lower().split())
            words2 = set(value_list[1].lower().split())
            overlap = words1 & words2
            return len(overlap) >= 2
    return False


def _dates_match(values: set) -> bool:
    """Check if dates are the same despite different formatting."""
    from backend.services.calculation_engine import parse_date
    parsed = set()
    for v in values:
        d = parse_date(v)
        if d:
            parsed.add(d.strftime('%Y-%m-%d'))
    return len(parsed) <= 1 and len(parsed) > 0


def _times_close(values: set, threshold_minutes: int = 30) -> bool:
    """Check if times are close enough (within threshold)."""
    times = []
    for v in values:
        try:
            parts = v.replace(' ', '').replace('AM', '').replace('PM', '').split(':')
            minutes = int(parts[0]) * 60 + int(parts[1])
            times.append(minutes)
        except:
            continue

    if len(times) < 2:
        return True

    max_diff = max(times) - min(times)
    return max_diff <= threshold_minutes


def _get_contradiction_impact(field_name: str) -> str:
    """Get the impact description for a contradiction."""
    impacts = {
        'vehicle_registration': 'Vehicle identity cannot be confirmed. This is a critical discrepancy that may indicate document errors.',
        'incident_date': 'Claim window calculation cannot be reliably evaluated. Timeline verification required.',
        'incident_time': 'Incident timeline has inconsistencies. May affect sequence of events verification.',
        'incident_location': 'Incident location is inconsistent across documents. Geographic coverage verification affected.',
        'customer_name': 'Claimant identity is inconsistent across documents. Ownership verification required.',
    }
    return impacts.get(field_name, 'Inconsistency detected — further investigation needed.')


def detect_exclusion_indicators(documents: Dict[str, str]) -> List[Dict]:
    """
    Detect indicators of policy exclusions from document content.
    Uses Gemini if available, with keyword fallback.
    """
    if gemini_service.is_available():
        result = _detect_exclusions_with_gemini(documents)
        if result:
            return result

    return _detect_exclusions_with_keywords(documents)


def _detect_exclusions_with_gemini(documents: Dict[str, str]) -> Optional[List[Dict]]:
    """Use Gemini to detect exclusion indicators."""
    docs_text = ""
    for doc_name, content in documents.items():
        docs_text += f"\n--- {doc_name} ---\n{content}\n"

    prompt = f"""Analyze these insurance claim documents for indicators of policy exclusions.
Look for evidence of:
- Alcohol or substance involvement
- Intentional damage
- Mechanical breakdown (not accident-caused)
- Wear and tear
- Commercial use of private vehicle
- Invalid or expired driving licence
- Unauthorized modifications

Documents:
{docs_text}

Return JSON:
{{
  "exclusion_indicators": [
    {{
      "type": "alcohol_involvement | intentional_damage | mechanical_breakdown | wear_and_tear | commercial_use | invalid_licence | unauthorized_modification",
      "evidence": "exact quote from document",
      "source_document": "document name",
      "confidence": 0.0-1.0,
      "explanation": "why this indicates an exclusion"
    }}
  ]
}}

If no exclusion indicators are found, return: {{"exclusion_indicators": []}}
Do NOT invent indicators. Only flag clear evidence from the documents."""

    result = gemini_service.generate_json(prompt)
    if result and 'exclusion_indicators' in result:
        return result['exclusion_indicators']
    return None


def _detect_exclusions_with_keywords(documents: Dict[str, str]) -> List[Dict]:
    """Keyword-based exclusion detection fallback."""
    indicators = []

    exclusion_keywords = {
        'alcohol_involvement': ['alcohol', 'drunk', 'intoxicat', 'under the influence', 'liquor', 'inebriat'],
        'intentional_damage': ['intentional', 'deliberately', 'self-inflict', 'staged', 'purposely'],
        'mechanical_breakdown': ['engine seizure', 'mechanical failure', 'electrical failure', 'breakdown', 'engine seized', 'gearbox fail'],
        'wear_and_tear': ['wear and tear', 'rust', 'corrosion', 'deteriorat', 'aging', 'gradual'],
        'commercial_use': ['ride-sharing', 'ride sharing', 'commercial', 'taxi', 'rental', 'goods transport', 'uber', 'ola'],
    }

    for doc_name, content in documents.items():
        content_lower = content.lower()
        for exc_type, keywords in exclusion_keywords.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    # Find the context
                    idx = content_lower.index(kw.lower())
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(kw) + 50)
                    snippet = content[start:end].strip()

                    indicators.append({
                        'type': exc_type,
                        'evidence': snippet,
                        'source_document': doc_name,
                        'confidence': 0.7,
                        'explanation': f'Keyword "{kw}" found indicating potential {exc_type.replace("_", " ")}'
                    })
                    break  # One match per type per document is enough

    return indicators

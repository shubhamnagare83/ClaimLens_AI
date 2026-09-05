"""
ClaimLens AI — Extraction Service
Uses Gemini for AI-powered fact extraction, with regex fallback.
"""
import re
import json
from typing import Dict, List, Optional
from backend.services import gemini_service


def extract_facts_from_documents(claim_id: str, documents: Dict[str, str]) -> Dict[str, list]:
    """
    Extract structured facts from all documents.
    Returns dict of field_name -> list of {value, source_document, evidence, confidence}.
    """
    # Try Gemini first
    gemini_result = _extract_with_gemini(claim_id, documents)
    if gemini_result:
        return gemini_result

    # Fallback to regex extraction
    return _extract_with_regex(claim_id, documents)


def _extract_with_gemini(claim_id: str, documents: Dict[str, str]) -> Optional[Dict]:
    """Use Gemini to extract facts from documents."""
    if not gemini_service.is_available():
        return None

    docs_text = ""
    for doc_name, content in documents.items():
        docs_text += f"\n--- DOCUMENT: {doc_name} ---\n{content}\n"

    prompt = f"""Extract structured facts from these insurance claim documents.
For each fact found, identify ALL occurrences across ALL documents.

Documents:
{docs_text}

Return a JSON object with this exact structure:
{{
  "customer_name": [
    {{"value": "...", "source_document": "...", "evidence": "exact text snippet", "confidence": 0.95}}
  ],
  "policy_number": [...],
  "vehicle_registration": [...],
  "vehicle_type": [...],
  "incident_type": [...],
  "incident_date": [...],
  "incident_time": [...],
  "incident_location": [...],
  "damage_parts": [...],
  "claim_date": [...],
  "repair_estimate_total": [...],
  "fir_number": [...],
  "keys_status": [...]
}}

Rules:
- Extract EVERY occurrence from EVERY document
- Keep dates in their original format as found in the document
- Include the exact text snippet as evidence
- Set confidence between 0.0 and 1.0
- If a field is not found, use an empty list
- Do NOT invent or infer values not present in the documents"""

    result = gemini_service.generate_json(prompt)
    if result and isinstance(result, dict):
        return result
    return None


def _extract_with_regex(claim_id: str, documents: Dict[str, str]) -> Dict[str, list]:
    """Fallback regex-based extraction."""
    facts = {
        'customer_name': [],
        'policy_number': [],
        'vehicle_registration': [],
        'vehicle_type': [],
        'incident_type': [],
        'incident_date': [],
        'incident_time': [],
        'incident_location': [],
        'damage_parts': [],
        'claim_date': [],
        'repair_estimate_total': [],
        'fir_number': [],
        'keys_status': [],
    }

    for doc_name, content in documents.items():
        _extract_from_text(doc_name, content, facts)

    return facts


def _extract_from_text(doc_name: str, text: str, facts: dict):
    """Extract facts from a single document using regex patterns."""
    lines = text.split('\n')

    # Registration number patterns
    reg_patterns = [
        r'(?:Registration\s*(?:Number|No\.?)|Reg\.?\s*No\.?|Vehicle\s*No\.?|Regn\.?\s*No\.?|Vehicle\s*Registration)\s*[:\s]*([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})',
        r'(?:registration|vehicle)\s+([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})',
        r'\b([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})\b',
    ]
    for pattern in reg_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            val = match.group(1).upper()
            if not any(f['value'] == val and f['source_document'] == doc_name
                      for f in facts['vehicle_registration']):
                facts['vehicle_registration'].append({
                    'value': val, 'source_document': doc_name,
                    'evidence': match.group(0).strip(), 'confidence': 0.9
                })

    # Date patterns
    date_patterns = [
        (r'(?:Date\s*of\s*Incident|Incident\s*Date)\s*[:\s]*(.+?)(?:\n|$)', 'incident_date'),
        (r'(?:Claim\s*Date|Date\s*of\s*Claim)\s*[:\s]*(.+?)(?:\n|$)', 'claim_date'),
    ]
    for pattern, field in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            val = match.group(1).strip()
            if val and len(val) > 4:
                facts[field].append({
                    'value': val, 'source_document': doc_name,
                    'evidence': match.group(0).strip(), 'confidence': 0.85
                })

    # Time patterns
    time_patterns = [
        r'(?:Incident\s*Time|Time\s*of\s*Incident|Time|Approx\.?\s*Time)\s*[:\s]*(\d{1,2}:\d{2}(?:\s*(?:AM|PM))?)',
    ]
    for pattern in time_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            facts['incident_time'].append({
                'value': match.group(1).strip(), 'source_document': doc_name,
                'evidence': match.group(0).strip(), 'confidence': 0.85
            })

    # Name patterns
    name_patterns = [
        r'(?:Name|Policyholder|Customer|Complainant)\s*[:\s]*([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    for pattern in name_patterns:
        for match in re.finditer(pattern, text):
            val = match.group(1).strip()
            if val and len(val) > 3:
                if not any(f['value'] == val and f['source_document'] == doc_name
                          for f in facts['customer_name']):
                    facts['customer_name'].append({
                        'value': val, 'source_document': doc_name,
                        'evidence': match.group(0).strip(), 'confidence': 0.85
                    })

    # Policy number
    pol_pattern = r'(?:Policy\s*(?:Number|No\.?))\s*[:\s]*(POL-\d{4}-\d{3})'
    for match in re.finditer(pol_pattern, text, re.IGNORECASE):
        facts['policy_number'].append({
            'value': match.group(1), 'source_document': doc_name,
            'evidence': match.group(0).strip(), 'confidence': 0.95
        })

    # Location
    loc_pattern = r'(?:Location)\s*[:\s]*(.+?)(?:\n|$)'
    for match in re.finditer(loc_pattern, text, re.IGNORECASE):
        val = match.group(1).strip()
        if val and len(val) > 3:
            facts['incident_location'].append({
                'value': val, 'source_document': doc_name,
                'evidence': match.group(0).strip(), 'confidence': 0.8
            })

    # Repair total
    total_pattern = r'(?:Total\s*(?:Estimate|Cost|Amount)?)\s*[:\s]*(?:Rs\.?\s*)?([0-9,]+)'
    for match in re.finditer(total_pattern, text, re.IGNORECASE):
        val = match.group(1).replace(',', '')
        if val.isdigit() and int(val) > 0:
            facts['repair_estimate_total'].append({
                'value': val, 'source_document': doc_name,
                'evidence': match.group(0).strip(), 'confidence': 0.9
            })

    # FIR number
    fir_pattern = r'FIR\s*(?:Number|No\.?)\s*[:\s]*(FIR-\S+)'
    for match in re.finditer(fir_pattern, text, re.IGNORECASE):
        facts['fir_number'].append({
            'value': match.group(1), 'source_document': doc_name,
            'evidence': match.group(0).strip(), 'confidence': 0.95
        })

    # Vehicle type
    if re.search(r'(?:Private\s*Car|Motor\s*Car|Car|LMV)', text, re.IGNORECASE):
        facts['vehicle_type'].append({
            'value': 'Car', 'source_document': doc_name,
            'evidence': 'Vehicle type identified as Car', 'confidence': 0.8
        })
    elif re.search(r'(?:Two-Wheeler|Two\s*Wheeler|Motor\s*Cycle|Scooter|MCWG)', text, re.IGNORECASE):
        facts['vehicle_type'].append({
            'value': 'Two-Wheeler', 'source_document': doc_name,
            'evidence': 'Vehicle type identified as Two-Wheeler', 'confidence': 0.8
        })

    # Incident type
    if re.search(r'(?:theft|stolen|missing)', text, re.IGNORECASE):
        facts['incident_type'].append({
            'value': 'Theft', 'source_document': doc_name,
            'evidence': 'Theft related content found', 'confidence': 0.8
        })
    elif re.search(r'(?:accident|collision|collided|crash|hit|damage)', text, re.IGNORECASE):
        facts['incident_type'].append({
            'value': 'Accident', 'source_document': doc_name,
            'evidence': 'Accident related content found', 'confidence': 0.8
        })

    # Keys status
    keys_pattern = r'(?:keys?\s+(?:currently\s+)?in\s+possession|keys?\s+submitted)\s*[:\s]*(\d+)'
    for match in re.finditer(keys_pattern, text, re.IGNORECASE):
        facts['keys_status'].append({
            'value': match.group(1), 'source_document': doc_name,
            'evidence': match.group(0).strip(), 'confidence': 0.85
        })
    if re.search(r'All keys accounted for', text, re.IGNORECASE):
        facts['keys_status'].append({
            'value': 'all_accounted', 'source_document': doc_name,
            'evidence': 'All keys accounted for', 'confidence': 0.9
        })
    if re.search(r'key\(s\) are unaccounted', text, re.IGNORECASE):
        facts['keys_status'].append({
            'value': 'keys_missing', 'source_document': doc_name,
            'evidence': 'Keys unaccounted for', 'confidence': 0.9
        })

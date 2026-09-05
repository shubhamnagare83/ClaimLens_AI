"""
ClaimLens AI — Calculation Engine
All deterministic calculations (dates, amounts, etc.)
NEVER ask Gemini to perform these calculations.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string in various formats."""
    if not date_str:
        return None

    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%d %B, %Y",
        "%d %b, %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def calculate_days_between(date1_str: str, date2_str: str) -> Optional[int]:
    """Calculate days between two date strings. Returns abs difference."""
    d1 = parse_date(date1_str)
    d2 = parse_date(date2_str)
    if d1 and d2:
        return abs((d2 - d1).days)
    return None


def check_claim_window(incident_date: str, claim_date: str, window_days: int = 7) -> dict:
    """Check if claim was filed within the notification window."""
    days = calculate_days_between(incident_date, claim_date)
    if days is None:
        return {
            'status': 'UNKNOWN',
            'days': None,
            'within_window': None,
            'message': 'Unable to calculate — date parsing failed'
        }

    within = days <= window_days
    if within:
        status = 'PASS'
        msg = f"Claim filed within {days} day(s) — within {window_days}-day window"
    elif days <= window_days * 2:
        status = 'WARNING'
        msg = f"Claim filed after {days} day(s) — beyond {window_days}-day window, reasonable delay may apply"
    else:
        status = 'FAIL'
        msg = f"Claim filed after {days} day(s) — significantly beyond {window_days}-day window"

    return {'status': status, 'days': days, 'within_window': within, 'message': msg}


def check_policy_validity(incident_date: str, policy_start: str, policy_end: str) -> dict:
    """Check if incident occurred within policy period."""
    inc = parse_date(incident_date)
    start = parse_date(policy_start)
    end = parse_date(policy_end)

    if not all([inc, start, end]):
        return {'status': 'UNKNOWN', 'valid': None, 'message': 'Unable to determine — missing dates'}

    if start <= inc <= end:
        return {'status': 'PASS', 'valid': True,
                'message': f'Incident on {incident_date} is within policy period ({policy_start} to {policy_end})'}
    elif inc < start:
        return {'status': 'FAIL', 'valid': False,
                'message': f'Incident on {incident_date} is BEFORE policy start ({policy_start})'}
    else:
        return {'status': 'FAIL', 'valid': False,
                'message': f'Incident on {incident_date} is AFTER policy end ({policy_end})'}


def check_idv_limit(repair_estimate: float, idv: float) -> dict:
    """Check if repair estimate exceeds IDV."""
    if idv <= 0:
        return {'status': 'UNKNOWN', 'within_idv': None, 'message': 'IDV not available'}
    if repair_estimate <= 0:
        return {'status': 'UNKNOWN', 'within_idv': None, 'message': 'Repair estimate not available'}

    ratio = repair_estimate / idv * 100
    if repair_estimate <= idv:
        return {
            'status': 'PASS', 'within_idv': True,
            'ratio': round(ratio, 1),
            'message': f'Repair estimate (Rs. {repair_estimate:,.0f}) is within IDV (Rs. {idv:,.0f}) — {ratio:.1f}%'
        }
    else:
        return {
            'status': 'WARNING', 'within_idv': False,
            'ratio': round(ratio, 1),
            'message': f'Repair estimate (Rs. {repair_estimate:,.0f}) EXCEEDS IDV (Rs. {idv:,.0f}) — {ratio:.1f}%'
        }


def check_total_loss(repair_estimate: float, idv: float, threshold: float = 0.75) -> dict:
    """Check if repair constitutes total loss."""
    if idv <= 0 or repair_estimate <= 0:
        return {'is_total_loss': False, 'ratio': 0, 'message': 'Insufficient data'}

    ratio = repair_estimate / idv
    is_total = ratio >= threshold
    return {
        'is_total_loss': is_total,
        'ratio': round(ratio * 100, 1),
        'threshold': threshold * 100,
        'message': f'Repair/IDV ratio: {ratio*100:.1f}% (threshold: {threshold*100}%)'
    }


def calculate_deductible(vehicle_type: str, voluntary_deductible: float = 0) -> dict:
    """Calculate applicable deductible."""
    compulsory = 2000 if vehicle_type == 'Car' else 1000
    total = compulsory + voluntary_deductible
    return {
        'compulsory': compulsory,
        'voluntary': voluntary_deductible,
        'total': total,
        'vehicle_type': vehicle_type,
        'message': f'Compulsory deductible: Rs. {compulsory:,} + Voluntary: Rs. {voluntary_deductible:,.0f} = Total: Rs. {total:,.0f}'
    }


def calculate_net_claim(repair_estimate: float, deductible: float, idv: float) -> dict:
    """Calculate net claim amount after deductible, capped at IDV."""
    if repair_estimate <= 0:
        return {'net_amount': 0, 'message': 'No repair estimate'}

    after_deductible = max(0, repair_estimate - deductible)
    net = min(after_deductible, idv) if idv > 0 else after_deductible

    return {
        'repair_estimate': repair_estimate,
        'deductible': deductible,
        'after_deductible': after_deductible,
        'idv_cap': idv,
        'net_amount': net,
        'message': f'Rs. {repair_estimate:,.0f} - Rs. {deductible:,.0f} = Rs. {after_deductible:,.0f} (capped at IDV: Rs. {idv:,.0f}) → Net: Rs. {net:,.0f}'
    }


def build_timeline(claim: dict) -> list:
    """Build a claim timeline with days between events."""
    events = []
    incident = parse_date(claim.get('incident_date', ''))
    claim_dt = parse_date(claim.get('claim_date', ''))
    policy_start = parse_date(claim.get('policy_start_date', ''))

    if policy_start:
        events.append({
            'event': 'Policy Start',
            'date': claim.get('policy_start_date', ''),
            'days_from_incident': -(incident - policy_start).days if incident else 0,
            'source': 'Policy'
        })
    if incident:
        events.append({
            'event': 'Incident',
            'date': claim.get('incident_date', ''),
            'days_from_incident': 0,
            'source': 'Claim Form'
        })
    if incident and claim_dt:
        events.append({
            'event': 'Claim Submitted',
            'date': claim.get('claim_date', ''),
            'days_from_incident': (claim_dt - incident).days,
            'source': 'Claim Form'
        })
    events.append({
        'event': 'AI Review',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'days_from_incident': (datetime.now() - incident).days if incident else 0,
        'source': 'System'
    })

    return events

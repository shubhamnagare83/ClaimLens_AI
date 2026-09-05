"""
ClaimLens AI — Simulation Service
'What-if' scenario recalculation.
"""
from typing import Dict
from backend.services import calculation_engine, policy_engine, completeness_engine
from backend.services import recommendation_engine
from backend.database import insert_simulation


def run_simulation(claim: Dict, documents: Dict[str, str],
                   extracted_facts: Dict, params: Dict) -> Dict:
    """
    Run a what-if simulation with modified parameters.
    Returns simulated result.
    """
    # Create modified claim
    sim_claim = dict(claim)

    if params.get('incident_date'):
        sim_claim['incident_date'] = params['incident_date']
    if params.get('claim_date'):
        sim_claim['claim_date'] = params['claim_date']
    if params.get('repair_amount') is not None:
        sim_claim['repair_estimate'] = params['repair_amount']

    # Simulate document changes
    sim_docs = dict(documents) if documents else {}
    if params.get('fir_present') is True and 'fir' not in sim_docs:
        sim_docs['fir'] = '[Simulated FIR document]'
    elif params.get('fir_present') is False and 'fir' in sim_docs:
        del sim_docs['fir']

    if params.get('keys_present') is True and 'key_declaration' not in sim_docs:
        sim_docs['key_declaration'] = '[Simulated key declaration]'
    elif params.get('keys_present') is False and 'key_declaration' in sim_docs:
        del sim_docs['key_declaration']

    if params.get('licence_valid') is True and 'driving_license' not in sim_docs:
        sim_docs['driving_license'] = '[Simulated valid driving license]'
    elif params.get('licence_valid') is False and 'driving_license' in sim_docs:
        del sim_docs['driving_license']

    # Simulate extracted facts modifications
    sim_facts = dict(extracted_facts) if extracted_facts else {}
    if params.get('licence_valid') is False:
        sim_facts['exclusion_indicators'] = [{'type': 'invalid_licence', 'confidence': 0.8}]

    # Re-run calculations
    calc = {
        'claim_window': calculation_engine.check_claim_window(
            sim_claim.get('incident_date', ''), sim_claim.get('claim_date', '')),
        'policy_validity': calculation_engine.check_policy_validity(
            sim_claim.get('incident_date', ''),
            sim_claim.get('policy_start_date', ''),
            sim_claim.get('policy_end_date', '')),
        'idv_check': calculation_engine.check_idv_limit(
            sim_claim.get('repair_estimate', 0), sim_claim.get('idv', 0)),
        'deductible': calculation_engine.calculate_deductible(sim_claim.get('vehicle_type', 'Car')),
    }

    # Re-evaluate policy
    policy_findings = policy_engine.evaluate_claim_against_policy(
        sim_claim, sim_docs, sim_facts)

    # Re-check completeness
    completeness = completeness_engine.check_completeness(sim_claim, sim_docs)

    # Detect exclusions
    exclusion_indicators = sim_facts.get('exclusion_indicators', [])

    # Re-check consistency (use existing - simulations don't change document content)
    from backend.services.consistency_engine import check_consistency
    consistency = check_consistency(sim_facts)

    # Generate recommendation
    result = recommendation_engine.generate_recommendation(
        policy_findings, consistency, completeness, exclusion_indicators, calc
    )

    sim_result = {
        'is_simulation': True,
        'label': 'SIMULATION ONLY',
        'parameters': params,
        'original_recommendation': claim.get('status', 'PENDING'),
        'simulated_recommendation': result['recommendation'],
        'simulated_confidence': result['confidence'],
        'simulated_evidence_score': result['evidence_score'],
        'calculations': calc,
        'explanation': result['explanation'],
        'changes_from_original': _describe_changes(claim, sim_claim, params),
    }

    # Save to database
    try:
        insert_simulation(claim['claim_id'], params, sim_result)
    except:
        pass

    return sim_result


def _describe_changes(original: Dict, simulated: Dict, params: Dict) -> list:
    changes = []
    if params.get('incident_date') and params['incident_date'] != original.get('incident_date'):
        changes.append(f"Incident date: {original.get('incident_date')} -> {params['incident_date']}")
    if params.get('claim_date') and params['claim_date'] != original.get('claim_date'):
        changes.append(f"Claim date: {original.get('claim_date')} -> {params['claim_date']}")
    if params.get('repair_amount') is not None:
        changes.append(f"Repair amount: Rs. {original.get('repair_estimate', 0):,.0f} -> Rs. {params['repair_amount']:,.0f}")
    if params.get('fir_present') is not None:
        changes.append(f"FIR present: {'Yes' if params['fir_present'] else 'No'}")
    if params.get('keys_present') is not None:
        changes.append(f"Keys present: {'Yes' if params['keys_present'] else 'No'}")
    if params.get('licence_valid') is not None:
        changes.append(f"Licence valid: {'Yes' if params['licence_valid'] else 'No'}")
    return changes

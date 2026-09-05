"""
ClaimLens AI — ML Inference & Risk Prediction Service
Uses LightGBM model trained on Kaggle Vehicle Insurance dataset
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import joblib

MODEL_DIR = Path(__file__).resolve().parent.parent / "ml"
MODEL_PATH = MODEL_DIR / "model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
BENCHMARKS_PATH = MODEL_DIR / "benchmarks.json"

_model = None
_metrics = None
_benchmarks = None


def get_model():
    global _model
    if _model is None and MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
    return _model


def get_metrics() -> Dict[str, Any]:
    global _metrics
    if _metrics is None and METRICS_PATH.exists():
        with open(METRICS_PATH, 'r', encoding='utf-8') as f:
            _metrics = json.load(f)
    return _metrics or {"error": "Metrics not found. Model needs training."}


def get_benchmarks() -> Dict[str, Any]:
    global _benchmarks
    if _benchmarks is None and BENCHMARKS_PATH.exists():
        with open(BENCHMARKS_PATH, 'r', encoding='utf-8') as f:
            _benchmarks = json.load(f)
    return _benchmarks or {"avg_payout_overall": 35000.0}


def predict_claim_risk(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run model inference and insurance heuristic anomaly scoring."""
    model = get_model()
    metrics = get_metrics()
    benchmarks = get_benchmarks()

    idv = float(data.get('insured_value') or data.get('idv') or 450000.0)
    repair_est = float(data.get('repair_estimate') or 0.0)
    prod_year = int(data.get('prod_year') or 2021)
    vehicle_age = max(0, min(40, 2026 - prod_year))
    premium = float(data.get('premium') or (idv * 0.03))
    ccm_ton = float(data.get('ccm_ton') or 1500.0)
    seats = int(data.get('seats_num') or 5)
    carrying = float(data.get('carrying_capacity') or 0.0)

    # Normalize vehicle type
    raw_vtype = str(data.get('type_vehicle') or data.get('vehicle_type') or 'Car')
    vtype_categories = metrics.get('categories', {}).get('type_vehicle', [])
    mapped_vtype = "Pick-up / Delivery Van"
    for cat in vtype_categories:
        if raw_vtype.lower() in cat.lower() or cat.lower() in raw_vtype.lower():
            mapped_vtype = cat
            break

    raw_usage = str(data.get('usage') or 'Private')
    usage_categories = metrics.get('categories', {}).get('usage', [])
    mapped_usage = "Private"
    for cat in usage_categories:
        if raw_usage.lower() in cat.lower() or cat.lower() in raw_usage.lower():
            mapped_usage = cat
            break

    # Feature calculation
    premium_ratio = float(min(1.0, premium / (idv + 1.0)))
    idv_log = float(np.log1p(max(0, idv)))

    # Run ML prediction if model available
    base_probability = 0.15
    if model is not None:
        try:
            row_df = pd.DataFrame([{
                'INSURED_VALUE': idv,
                'PREMIUM': premium,
                'VEHICLE_AGE': vehicle_age,
                'SEATS_NUM': seats,
                'CARRYING_CAPACITY': carrying,
                'CCM_TON': ccm_ton,
                'PREMIUM_RATIO': premium_ratio,
                'IDV_LOG': idv_log,
                'TYPE_VEHICLE': mapped_vtype,
                'USAGE': mapped_usage
            }])
            for col in ['TYPE_VEHICLE', 'USAGE']:
                row_df[col] = row_df[col].astype('category')
            probs = model.predict_proba(row_df)[0]
            base_probability = float(probs[1])
        except Exception as e:
            print(f"Inference error: {e}")

    # Heuristics & Anomaly detection
    anomalies = []
    benchmark_payout = benchmarks.get('payout_by_vehicle_type', {}).get(
        mapped_vtype, benchmarks.get('avg_payout_overall', 36000.0)
    )

    overclaim_ratio = 1.0
    if repair_est > 0:
        overclaim_ratio = repair_est / max(1.0, benchmark_payout)
        if repair_est > (idv * 0.75):
            anomalies.append({
                "type": "CONSTRUCTIVE_TOTAL_LOSS_RISK",
                "severity": "HIGH",
                "description": f"Repair estimate (₹{repair_est:,.0f}) exceeds 75% of vehicle IDV (₹{idv:,.0f}). Requires salvage assessment."
            })
        elif overclaim_ratio > 1.8:
            anomalies.append({
                "type": "INFLATED_REPAIR_ESTIMATE",
                "severity": "MEDIUM",
                "description": f"Claim amount is {overclaim_ratio:.1f}x the historical median payout (₹{benchmark_payout:,.0f}) for this vehicle class."
            })

    if vehicle_age > 10 and repair_est > (idv * 0.5):
        anomalies.append({
            "type": "HIGH_AGE_HIGH_CLAIM_RATIO",
            "severity": "MEDIUM",
            "description": f"Vehicle is {vehicle_age} years old with substantial claim value. Check for pre-existing wear and tear."
        })

    if premium_ratio < 0.01:
        anomalies.append({
            "type": "LOW_PREMIUM_UNDERWRITING_RISK",
            "severity": "LOW",
            "description": "Policy premium is unusually low relative to insured declared value."
        })

    # Combined Risk Score (0 - 100)
    # 50% from ML Model probability, 50% from anomaly severity
    anomaly_penalty = sum(25 if a['severity'] == 'HIGH' else (15 if a['severity'] == 'MEDIUM' else 8) for a in anomalies)
    ml_component = min(100.0, base_probability * 180.0)
    risk_score = round(min(100.0, (ml_component * 0.5) + (anomaly_penalty * 0.5)), 1)

    if risk_score >= 70 or any(a['severity'] == 'HIGH' for a in anomalies):
        risk_level = "HIGH RISK"
        recommendation = "SPECIAL INVESTIGATION UNIT (SIU) & FORENSIC GARAGE AUDIT"
        badge_class = "risk-high"
    elif risk_score >= 40 or len(anomalies) > 0:
        risk_level = "MODERATE RISK"
        recommendation = "DOCUMENT CROSS-VERIFICATION & PARTS DEPRECIATION CHECK"
        badge_class = "risk-medium"
    else:
        risk_level = "LOW RISK"
        recommendation = "FAST-TRACK SETTLEMENT APPROVAL"
        badge_class = "risk-low"

    return {
        "claim_probability": round(base_probability * 100, 2),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "badge_class": badge_class,
        "recommendation": recommendation,
        "benchmark_payout": round(benchmark_payout, 2),
        "claimed_amount": repair_est,
        "overclaim_ratio": round(overclaim_ratio, 2),
        "anomalies": anomalies,
        "vehicle_details": {
            "mapped_vehicle_type": mapped_vtype,
            "mapped_usage": mapped_usage,
            "vehicle_age_years": vehicle_age,
            "idv": idv,
            "premium": premium
        },
        "model_version": "ClaimLens-LightGBM-v1.0 (508k Kaggle records)"
    }

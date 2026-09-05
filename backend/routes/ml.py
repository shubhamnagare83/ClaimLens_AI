"""
ClaimLens AI — Machine Learning Routes
Endpoints for Model Performance, Accuracy Metrics & Claim Risk Inference
"""
from fastapi import APIRouter, HTTPException
from backend.services import ml_service
from backend.models import MLPredictRequest
from backend.database import get_claim

router = APIRouter()


@router.get("/api/ml/metrics")
async def get_model_metrics():
    """Return LightGBM model performance metrics trained on Kaggle dataset."""
    metrics = ml_service.get_metrics()
    benchmarks = ml_service.get_benchmarks()
    return {
        "metrics": metrics,
        "benchmarks": benchmarks
    }


@router.post("/api/ml/predict")
async def predict_risk(req: MLPredictRequest):
    """Run live risk prediction and payout anomaly detection on custom vehicle data."""
    try:
        result = ml_service.predict_claim_risk(req.model_dump())
        return result
    except Exception as e:
        raise HTTPException(500, f"ML prediction failed: {str(e)}")


@router.get("/api/ml/claim-prediction/{claim_id}")
async def predict_claim_by_id(claim_id: str):
    """Run ML risk assessment for a specific claim in the database."""
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    # Map vehicle type and parameters
    v_type = claim.get('vehicle_type', 'Car')
    idv = float(claim.get('idv') or 450000.0)
    repair = float(claim.get('repair_estimate') or 0.0)

    input_data = {
        'insured_value': idv,
        'repair_estimate': repair,
        'type_vehicle': 'Pick-up / Delivery Van' if v_type == 'Car' else 'Motor-cycle',
        'usage': 'Private',
        'prod_year': 2021,
        'premium': idv * 0.035,
        'ccm_ton': 1500 if v_type == 'Car' else 150,
        'seats_num': 5 if v_type == 'Car' else 2
    }

    result = ml_service.predict_claim_risk(input_data)
    result['claim_id'] = claim_id
    result['customer_name'] = claim.get('customer_name')
    result['vehicle_registration'] = claim.get('vehicle_registration')
    return result

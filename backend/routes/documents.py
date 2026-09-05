"""
ClaimLens AI — Documents & PDF AI Extraction Routes
Provides upload, multi-engine PDF parsing, entity extraction,
sample document browsing, and 1-click claim creation from uploaded files.
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from backend.database import (
    get_claim, insert_document, get_claim_documents, insert_claim,
    get_all_claims, update_claim
)
from backend.services import document_service, audit_service, report_service


router = APIRouter()

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "sample_documents"


@router.post("/api/documents/extract")
async def extract_uploaded_document(file: UploadFile = File(...)):
    """
    Extract text, classify document type, and extract insurance entities
    from any uploaded PDF, DOCX, TXT, or CSV file.
    """
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(400, "Uploaded file is empty.")

        parsed = document_service.parse_document_bytes(content_bytes, file.filename)
        return {
            "status": "success",
            "filename": parsed["filename"],
            "extension": parsed["extension"],
            "file_size": parsed["file_size"],
            "page_count": parsed["page_count"],
            "engine": parsed["engine"],
            "document_type": parsed["document_type"],
            "classification_confidence": parsed["classification_confidence"],
            "classification_reasons": parsed["classification_reasons"],
            "entities": parsed["entities"],
            "text_preview": parsed["text"][:1500] if parsed["text"] else "",
            "text_full": parsed["text"]
        }
    except Exception as e:
        raise HTTPException(500, f"Error processing document: {str(e)}")


@router.get("/api/documents/sample-files")
async def list_sample_documents():
    """
    List pre-generated realistic sample motor insurance claim PDFs available for testing.
    """
    samples = []
    if SAMPLE_DOCS_DIR.exists():
        for f in SAMPLE_DOCS_DIR.glob("*.pdf"):
            stat = f.stat()
            # Determine human-friendly category
            cat = "General"
            desc = "Sample claim document"
            if "Claim_Form" in f.name:
                cat = "Claim Form"
                desc = "Official Motor Vehicle Accident Intimation Form (Private Car Honda City)"
            elif "Repair_Estimate" in f.name:
                cat = "Repair Estimate"
                desc = "Authorized Garage Itemized Repair Quotation (Parts & Labour Breakdown)"
            elif "Theft_FIR" in f.name:
                cat = "Police FIR"
                desc = "State Police First Information Report for stolen two-wheeler (Royal Enfield)"
            elif "Taxi" in f.name:
                cat = "High Risk / Overclaim"
                desc = "Commercial Yellow-Plate taxi estimate with inflated amount and policy exclusion"

            samples.append({
                "filename": f.name,
                "category": cat,
                "description": desc,
                "size_bytes": stat.st_size,
                "size_formatted": f"{stat.st_size / 1024:.1f} KB"
            })
    return {"samples": samples, "total": len(samples)}


@router.post("/api/documents/scan-sample/{filename}")
async def scan_sample_document(filename: str):
    """
    Scan one of the pre-generated sample PDFs and return AI extracted entities.
    """
    filepath = SAMPLE_DOCS_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, f"Sample file {filename} not found.")

    content_bytes = filepath.read_bytes()
    parsed = document_service.parse_document_bytes(content_bytes, filename)
    return {
        "status": "success",
        "filename": parsed["filename"],
        "extension": parsed["extension"],
        "file_size": parsed["file_size"],
        "page_count": parsed["page_count"],
        "engine": parsed["engine"],
        "document_type": parsed["document_type"],
        "classification_confidence": parsed["classification_confidence"],
        "classification_reasons": parsed["classification_reasons"],
        "entities": parsed["entities"],
        "text_preview": parsed["text"][:1500] if parsed["text"] else "",
        "text_full": parsed["text"]
    }


@router.post("/api/documents/create-claim-from-file")
async def create_claim_from_file(file: UploadFile = File(...)):
    """
    Upload a PDF / document, extract its entities, automatically create a new claim case,
    attach the document, and trigger an initial ClaimLens AI cross-document review!
    """
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(400, "Uploaded file is empty.")

    parsed = document_service.parse_document_bytes(content_bytes, file.filename)
    entities = parsed["entities"]

    # Generate identifiers and defaults
    claim_id = f"CLM{str(uuid.uuid4())[:8].upper()}"
    policy_number = entities.get("policy_number") or f"POL-2024-{str(uuid.uuid4())[:3].upper()}"
    customer_name = entities.get("customer_name") or "Policyholder (From PDF)"
    vehicle_type = entities.get("vehicle_type") or "Car"
    vehicle_registration = entities.get("vehicle_registration") or "DL01AB1234"
    incident_type = "Theft" if parsed["document_type"] == "fir" else "Accident"
    incident_date = entities.get("incident_date") or "2024-11-12"
    incident_time = entities.get("incident_time") or "14:30"
    incident_location = entities.get("incident_location") or "Bengaluru"
    claim_date = "2024-11-13"
    repair_estimate = entities.get("repair_estimate_total") or 48500.0
    idv = 650000.0 if vehicle_type == "Car" else 180000.0
    deductible = 2000.0 if vehicle_type == "Car" else 1000.0

    claim_data = {
        'claim_id': claim_id,
        'policy_number': policy_number,
        'customer_name': customer_name,
        'vehicle_type': vehicle_type,
        'vehicle_registration': vehicle_registration,
        'incident_type': incident_type,
        'incident_date': incident_date,
        'incident_time': incident_time,
        'incident_location': incident_location,
        'claim_date': claim_date,
        'policy_start_date': '2024-01-01',
        'policy_end_date': '2025-01-01',
        'idv': idv,
        'repair_estimate': repair_estimate,
        'deductible': deductible,
        'status': 'PENDING',
    }

    result = insert_claim(claim_data)
    if not result:
        raise HTTPException(500, "Failed to insert claim into database.")

    audit_service.log_claim_created(claim_id)

    # Attach the uploaded document
    doc_type_key = parsed["document_type"]
    insert_document(claim_id, doc_type_key, file.filename, parsed["text"])
    audit_service.log_document_uploaded(claim_id, doc_type_key, file.filename)

    # If it's a repair estimate, also create a baseline claim form so cross-referencing has context
    if doc_type_key == "repair_estimate":
        simulated_claim_form = f"""MOTOR CLAIM FORM
Claim ID: {claim_id}
Policy Number: {policy_number}
Insured Name: {customer_name}
Vehicle Registration: {vehicle_registration}
Vehicle Type: {vehicle_type}
Date of Incident: {incident_date}
Time of Incident: {incident_time}
Location: {incident_location}
Estimated Repair Amount: Rs. {repair_estimate:,.2f}
Incident Description: Vehicle suffered frontal and bumper damage as documented in repair estimate.
"""
        insert_document(claim_id, "claim_form", "claim_form.txt", simulated_claim_form)
        audit_service.log_document_uploaded(claim_id, "claim_form", "claim_form.txt")

    elif doc_type_key == "fir":
        simulated_claim_form = f"""MOTOR THEFT CLAIM FORM
Claim ID: {claim_id}
Policy Number: {policy_number}
Insured Name: {customer_name}
Vehicle Registration: {vehicle_registration}
Vehicle Type: {vehicle_type}
Date of Incident: {incident_date}
FIR Reference: {entities.get('fir_number') or 'FIR-2024-051'}
Keys Accounted: All keys accounted for
Incident Description: Vehicle was stolen from public parking and police FIR registered.
"""
        insert_document(claim_id, "claim_form", "claim_form.txt", simulated_claim_form)
        audit_service.log_document_uploaded(claim_id, "claim_form", "claim_form.txt")

    # Run immediate claim evaluation
    review_output = report_service.run_full_review(claim_id)

    return {
        "status": "success",
        "claim_id": claim_id,
        "message": f"Claim {claim_id} successfully created and reviewed from uploaded PDF!",
        "extracted_entities": entities,
        "review_summary": {
            "recommendation": review_output.get("recommendation"),
            "confidence": review_output.get("confidence"),
            "contradiction_count": len(review_output.get("contradictions", [])),
            "red_flags": len(review_output.get("red_flags", [])),
            "payable_amount": review_output.get("financials", {}).get("net_claim_after_deductible")
        }
    }


# Standard endpoints for existing claims
@router.post("/api/claims/{claim_id}/documents")
async def upload_document(claim_id: str, file: UploadFile = File(...), doc_slot: Optional[str] = Form(None)):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    content_bytes = await file.read()
    parsed = document_service.parse_document_bytes(content_bytes, file.filename)
    content = parsed["text"]

    doc_type = doc_slot or parsed["document_type"]
    insert_document(claim_id, doc_type, file.filename, content)
    audit_service.log_document_uploaded(claim_id, doc_type, file.filename)

    # Re-run review after new document upload
    updated_review = report_service.run_full_review(claim_id)

    return {
        "claim_id": claim_id,
        "filename": file.filename,
        "document_type": doc_type,
        "content_length": len(content),
        "status": "uploaded_and_evaluated",
        "recommendation": updated_review.get("recommendation"),
        "confidence": updated_review.get("confidence")
    }


@router.get("/api/claims/{claim_id}/documents")
async def list_documents(claim_id: str):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    docs = get_claim_documents(claim_id)
    return {"claim_id": claim_id, "documents": docs}


@router.get("/api/claims/{claim_id}/documents/{doc_type}")
async def get_document_content(claim_id: str, doc_type: str):
    docs = get_claim_documents(claim_id)
    for doc in docs:
        if doc['document_type'] == doc_type:
            return {
                "claim_id": claim_id,
                "document_type": doc_type,
                "filename": doc['filename'],
                "content": doc['content'],
            }
    raise HTTPException(404, f"Document {doc_type} not found for claim {claim_id}")

"""
ClaimLens AI — Pydantic Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    ESCALATE = "ESCALATE"
    PENDING = "PENDING"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MatchStatus(str, Enum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    CONTRADICTION = "CONTRADICTION"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class ExtractedFact(BaseModel):
    field_name: str = ""
    value: str = ""
    source_document: str = ""
    page: int = 1
    evidence: str = ""
    confidence: float = 0.0


class FactExtractionResult(BaseModel):
    claim_id: str = ""
    facts: List[ExtractedFact] = Field(default_factory=list)


class ConsistencyCheck(BaseModel):
    field_name: str = ""
    values: Dict[str, str] = Field(default_factory=dict)
    status: str = "UNKNOWN"
    severity: str = "LOW"
    details: str = ""


class PolicyFinding(BaseModel):
    clause_id: str = ""
    title: str = ""
    rule: str = ""
    status: str = "PASS"  # PASS, FAIL, WARNING, UNKNOWN
    evidence: str = ""
    source_document: str = ""
    calculation: str = ""
    confidence: str = "HIGH"


class ContradictionFinding(BaseModel):
    field_name: str = ""
    severity: str = "LOW"
    values: Dict[str, str] = Field(default_factory=dict)
    impact: str = ""
    action: str = ""


class MissingInformation(BaseModel):
    document_type: str = ""
    description: str = ""
    required_by: List[str] = Field(default_factory=list)
    impact: str = ""


class Citation(BaseModel):
    source_document: str = ""
    page: int = 1
    evidence_snippet: str = ""
    policy_clause: str = ""


class EvidenceMatrixEntry(BaseModel):
    requirement: str = ""
    policy_clause: str = ""
    evidence: str = ""
    source: str = ""
    status: str = "UNKNOWN"
    confidence: str = "LOW"


class TimelineEvent(BaseModel):
    event: str = ""
    date: str = ""
    days_from_incident: int = 0
    source: str = ""


class ClaimReport(BaseModel):
    claim_id: str = ""
    recommendation: str = "PENDING"
    human_review_required: bool = True
    confidence: str = "LOW"
    evidence_score: float = 0.0
    evidence_score_breakdown: Dict[str, float] = Field(default_factory=dict)
    documents: Dict[str, Any] = Field(default_factory=dict)
    facts: Dict[str, Any] = Field(default_factory=dict)
    policy_findings: List[Dict] = Field(default_factory=list)
    contradictions: List[Dict] = Field(default_factory=list)
    missing_information: List[Dict] = Field(default_factory=list)
    calculations: List[Dict] = Field(default_factory=list)
    citations: List[Dict] = Field(default_factory=list)
    timeline: List[Dict] = Field(default_factory=list)
    evidence_matrix: List[Dict] = Field(default_factory=list)
    handoff: Optional[Dict] = None
    what_would_change: List[Dict] = Field(default_factory=list)
    explanation: str = ""
    disclaimer: str = "This recommendation is decision support. Final claim determination remains with an authorized human investigator."


class SimulationRequest(BaseModel):
    incident_date: Optional[str] = None
    claim_date: Optional[str] = None
    repair_amount: Optional[float] = None
    fir_present: Optional[bool] = None
    keys_present: Optional[bool] = None
    licence_valid: Optional[bool] = None


class ClaimCreateRequest(BaseModel):
    customer_name: str
    vehicle_type: str = "Car"
    vehicle_registration: str
    incident_type: str = "Accident"
    incident_date: str
    incident_time: str = ""
    incident_location: str = ""
    claim_date: str
    policy_number: str = ""
    policy_start_date: str = ""
    policy_end_date: str = ""
    idv: float = 0
    repair_estimate: float = 0
    deductible: float = 0
    description: Optional[str] = None


class ClaimUpdateRequest(BaseModel):
    customer_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_registration: Optional[str] = None
    incident_type: Optional[str] = None
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    incident_location: Optional[str] = None
    claim_date: Optional[str] = None
    policy_number: Optional[str] = None
    policy_start_date: Optional[str] = None
    policy_end_date: Optional[str] = None
    idv: Optional[float] = None
    repair_estimate: Optional[float] = None
    deductible: Optional[float] = None
    status: Optional[str] = None


class MLPredictRequest(BaseModel):
    insured_value: float = 450000
    premium: float = 12000
    prod_year: int = 2021
    type_vehicle: str = "Pick-up / Delivery Van"
    usage: str = "Private"
    ccm_ton: float = 1498
    seats_num: int = 5
    carrying_capacity: float = 0
    repair_estimate: Optional[float] = None


class AssistantChatRequest(BaseModel):
    message: str
    claim_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)



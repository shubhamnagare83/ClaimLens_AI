TRACK_ID=PS02

# ClaimLens AI — Evidence-first Motor Insurance Claim Investigation

**Tagline:** AI-powered evidence review assistant for motor insurance claims — cross-referencing documents, detecting contradictions, grounding every finding to source evidence, and escalating uncertain cases to human investigators.

---

## What It Does

ClaimLens AI is an **evidence review assistant** for motor insurance claims involving:
- **Cars and Two-wheelers** — accidents and theft
- **Three document types**: Claim Form, Repair Estimate / FIR, Customer Incident Statement

The system reviews submitted documents against a **fictional motor insurance policy** covering:
- Coverage rules (Section 1 — Own Damage, Theft)
- Exclusions (commercial use, intoxication, expired license, racing, consequential loss)
- Insured Declared Value (IDV) limits and deductibles
- Claim window requirements (48h accident, 24h theft FIR)
- Required documents per incident type

### What It Produces

For each claim, the system generates a **structured claim review** containing:

1. **Document Completeness Check** — whether all required documents are present
2. **Cross-Document Consistency** — fuzzy matching of vehicle registration, dates, locations, amounts across all submitted documents
3. **Contradiction Detection** — contradictions between documents are surfaced with severity, not smoothed over
4. **Policy Clause Evaluation** — which clauses apply, whether they support or block the claim, cited to specific documents and clauses
5. **Calculations** — claim window validity, policy period check, IDV limit, total loss assessment, net claim after deductible
6. **Evidence-Grounded Recommendation** — APPROVE, REJECT, ESCALATE, or REQUEST_INFORMATION
7. **Citations** — every finding traced to the document and clause it came from
8. **What-Would-Change Analysis** — what missing information would change the recommendation
9. **Investigator Handoff Brief** — structured summary for human review

### Key Design Decisions

- **Contradictions are surfaced, not smoothed**: The system explicitly flags mismatches in registration numbers, dates, and amounts between documents.
- **Uncertain cases are escalated**: When evidence is ambiguous or insufficient, the system recommends ESCALATE rather than making a determination.
- **Deterministic logic + GenAI reasoning**: Policy rules, calculations, and consistency checks use deterministic code. Gemini AI provides natural language explanations when available, but the system works fully without it (deterministic fallback mode).
- **Human-in-the-loop**: The system is an assistant — it provides evidence-grounded findings for the investigator, not autonomous decisions.

---

## How to Run

### Prerequisites
- Python 3.11+
- (Optional) Set `GEMINI_API_KEY` environment variable for AI-enhanced explanations

### Quick Start

```bash
pip install -r requirements.txt
python app.py
```

The application starts on **http://localhost:8000** — frontend and backend served together, no second command needed.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | No | Gemini API key for AI explanations. System works without it in deterministic mode. |

---

## Architecture

```
ClaimAI/
├── app.py                    ← Single entry point, starts everything on port 8000
├── requirements.txt          ← All Python dependencies
├── README.md                 ← This file
├── backend/
│   ├── config.py             ← Configuration and paths
│   ├── database.py           ← SQLite database (in-memory, seeded at startup)
│   ├── models.py             ← Pydantic request models
│   ├── ml/                   ← Pre-trained LightGBM model + metrics
│   │   ├── model.joblib      ← Trained model (committed, no runtime training)
│   │   ├── metrics.json      ← Model performance metrics
│   │   └── benchmarks.json   ← Vehicle-class payout benchmarks
│   ├── routes/
│   │   ├── health.py         ← Health check endpoint
│   │   ├── claims.py         ← CRUD operations for claims
│   │   ├── documents.py      ← Document management
│   │   ├── review.py         ← Evidence review pipeline trigger
│   │   ├── analytics.py      ← Dashboard statistics
│   │   └── ml.py             ← ML risk prediction endpoints
│   ├── services/
│   │   ├── report_service.py         ← Orchestrates the full review pipeline
│   │   ├── extraction_service.py     ← Fact extraction from documents
│   │   ├── consistency_engine.py     ← Cross-document consistency checks
│   │   ├── completeness_engine.py    ← Document completeness verification
│   │   ├── policy_engine.py          ← Policy clause evaluation
│   │   ├── calculation_engine.py     ← Deterministic calculations
│   │   ├── recommendation_engine.py  ← Evidence-grounded recommendation
│   │   ├── citation_service.py       ← Citation generation
│   │   ├── simulation_service.py     ← What-if scenario simulation
│   │   ├── retrieval_service.py      ← RAG-based policy retrieval (FAISS)
│   │   ├── gemini_service.py         ← Gemini API integration
│   │   ├── ml_service.py             ← LightGBM inference
│   │   ├── ml_trainer.py             ← Model training script (Kaggle data)
│   │   ├── audit_service.py          ← Audit trail logging
│   │   └── document_service.py       ← Document handling utilities
│   └── utils/                ← Shared utilities
├── data/
│   ├── policy/               ← Motor insurance policy documents (self-generated)
│   │   ├── motor_policy.json ← Full structured policy
│   │   ├── motor_policy.txt  ← Policy in plain text
│   │   ├── coverage_rules.json
│   │   ├── exclusions.json
│   │   └── required_documents.json
│   ├── claims/               ← Demo claim scenarios with documents
│   │   ├── claims_master.csv ← Master claim index (80+ claims)
│   │   ├── accident/         ← Clean accident claims
│   │   ├── theft/            ← Theft claims
│   │   ├── contradictions/   ← Claims with cross-document contradictions
│   │   ├── exclusions/       ← Claims triggering policy exclusions
│   │   ├── missing_documents/← Claims with incomplete submissions
│   │   └── ambiguous/        ← Ambiguous/edge-case claims
│   ├── embeddings/           ← Pre-computed FAISS index for policy retrieval
│   └── generated/            ← LLM-generated data artifacts
├── frontend/
│   ├── index.html            ← Single-page application
│   ├── app.js                ← Frontend logic
│   ├── styles.css            ← UI styling
│   └── banners/              ← Dashboard banner images
└── scripts/                  ← Data generation and training scripts
```

---

## Data and Documents

All data is **self-generated** — no external datasets are provided by the problem statement.

### Motor Insurance Policy
A fictional comprehensive motor insurance policy (`data/policy/`) covering:
- **Section 1 Coverage**: Own Damage (accident), Theft (total loss)
- **Exclusions**: Commercial use on private policy, intoxication, expired license, racing, consequential loss, war/nuclear
- **Claim Windows**: 48 hours for accidents, 24 hours for theft FIR
- **Required Documents**: Per incident type (claim form, repair estimate, FIR, customer statement, keys)
- **IDV and Deductibles**: Vehicle-type based limits

### Demo Claims (80+ scenarios)
Generated claim scenarios across 7 categories:
- **Clean Accident** — straightforward approval case
- **Clean Theft** — valid theft with FIR and key surrender
- **Missing Documents** — incomplete submission requiring information request
- **Contradictory Evidence** — mismatches between documents (dates, locations, amounts)
- **Policy Exclusion** — claims blocked by policy exclusions
- **Ambiguous** — borderline cases requiring investigator escalation
- **Difficult Theft** — theft with suspicious circumstances

Each claim includes realistic documents: claim forms, repair estimates, FIRs, and customer statements with deliberate inconsistencies in the difficult scenarios.

### ML Training Data
LightGBM model trained on the **Kaggle Vehicle Insurance Dataset** (`imtkaggleteam/vehicle-insurance-data`) — 508,499 records. The trained model (`backend/ml/model.joblib`) is committed and loaded at startup (no runtime training needed).

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Evidence Review Pipeline** | 17-step pipeline: document parsing → fact extraction → consistency check → completeness → exclusion detection → policy evaluation → recommendation → citation |
| **Contradiction Detection** | Cross-document fuzzy matching for registration numbers, dates, locations, amounts |
| **Policy Grounding** | Every finding cited to specific policy clauses and source documents |
| **ESCALATE, Don't Decide** | Ambiguous or insufficient evidence triggers escalation, not automatic determination |
| **What-If Simulator** | Modify claim parameters and see how the recommendation changes |
| **ML Risk Engine** | LightGBM model (91.38% accuracy, 0.743 ROC-AUC) for anomaly detection |
| **Audit Trail** | Every action logged: document upload, fact extraction, contradiction detection, recommendation |
| **Deterministic Fallback** | Full functionality without Gemini API — deterministic logic handles all critical paths |

---

## Demo Video

📹 [Demo Video Link](https://youtu.be/YOUR_DEMO_VIDEO_LINK)

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Database**: SQLite (in-memory, seeded at startup)
- **ML**: LightGBM, scikit-learn, pandas, numpy
- **RAG**: FAISS (local), Gemini Embeddings (gemini-embedding-001)
- **LLM**: Google Gemini API (optional, deterministic fallback)
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js
- **Serialization**: joblib (model), JSON (policy, metrics)

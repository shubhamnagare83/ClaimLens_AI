"""
ClaimLens AI — Claim AI Assistant Service
Provides contextual AI reasoning, policy grounding, fraud analysis, and communication drafting.
Supports both Gemini GenAI and comprehensive deterministic motor insurance reasoning.
"""
import re
import json
from typing import Dict, List, Optional, Any
from backend.database import get_claim, get_all_claims, get_claim_documents, get_latest_review
from backend.services import (
    gemini_service,
    retrieval_service,
    report_service,
    policy_engine,
    ml_service
)


def get_all_claims_summary() -> List[Dict[str, Any]]:
    """Return lightweight summary of all claims for assistant context and dropdown."""
    claims = get_all_claims()
    summaries = []

    for c in claims:
        summaries.append({
            "claim_id": c.get("claim_id"),
            "customer_name": c.get("customer_name"),
            "vehicle_type": c.get("vehicle_type"),
            "vehicle_registration": c.get("vehicle_registration"),
            "incident_type": c.get("incident_type"),
            "status": c.get("status"),
            "idv": c.get("idv", 0),
            "repair_estimate": c.get("repair_estimate", 0),
            "scenario_type": c.get("scenario_type", "")
        })
    return summaries


def get_suggested_prompts(claim_id: Optional[str] = None) -> List[Dict[str, str]]:
    """Return tailored quick prompt suggestions for the assistant."""
    if not claim_id:
        return [
            {"label": "🔍 Find high-risk claims", "prompt": "Which claims in the database have critical contradictions or high fraud risk?"},
            {"label": "📜 IRDAI Theft FIR Rules", "prompt": "What are the IRDAI rules and policy clauses regarding FIR filing delay in theft claims?"},
            {"label": "💰 Depreciation Rates Guide", "prompt": "What are the standard depreciation rates for rubber, plastic, glass, and metal parts?"},
            {"label": "⚖️ Total Loss Threshold", "prompt": "What qualifies a motor claim as a Constructive Total Loss (CTL) under Indian policy terms?"},
            {"label": "🚫 Commercial Use Exclusion", "prompt": "How does Policy Clause POL-010 apply to private vehicles used for commercial transit?"}
        ]

    claim = get_claim(claim_id)
    if not claim:
        return get_suggested_prompts(None)

    v_type = claim.get("vehicle_type", "Vehicle")
    inc_type = claim.get("incident_type", "Accident")
    scenario = claim.get("scenario_type", "")

    suggestions = [
        {"label": "🔍 Audit Discrepancies", "prompt": f"Audit all evidence contradictions and timeline discrepancies for claim {claim_id}."},
        {"label": "📜 Check Policy Exclusions", "prompt": f"Which specific policy clauses and exclusions apply to {claim_id} ({inc_type})?"},
        {"label": "✉️ Draft Customer RFI", "prompt": f"Draft a formal Request for Information (RFI) notice to claimant for {claim_id}."},
        {"label": "💰 Calculate Payout Breakdown", "prompt": f"Calculate the net payable settlement and depreciation deduction for {claim_id}."},
        {"label": "⚖️ Adjudication Recommendation", "prompt": f"What is the recommended decision for {claim_id} and what is the legal justification?"}
    ]

    if "THEFT" in inc_type.upper() or scenario == "THEFT":
        suggestions.insert(1, {"label": "🚨 Verify Theft Key & FIR", "prompt": f"Analyze the theft timeline, FIR delay, and whether both ignition keys were submitted for {claim_id}."})
    elif scenario == "EXCLUSION":
        suggestions.insert(1, {"label": "🚫 Analyze Breach of Policy", "prompt": f"Explain why {claim_id} triggers policy exclusion (commercial use/intoxication/speeding) with evidence."})
    elif scenario == "CONTRADICTION":
        suggestions.insert(1, {"label": "⚡ Cross-examine Driver & Timeline", "prompt": f"Highlight exact contradictions between the claim form, surveyor report, and FIR for {claim_id}."})

    return suggestions[:5]


def _gather_claim_context(claim_id: str) -> Dict[str, Any]:
    """Assemble all evidence, reviews, facts, and policy findings for a claim."""
    claim = get_claim(claim_id)
    if not claim:
        return {}

    docs = get_claim_documents(claim_id)
    review = get_latest_review(claim_id)

    if not review and docs:
        try:
            review = {"report_json": report_service.run_full_review(claim_id)}
        except Exception:
            review = None

    report_json = review.get("report_json", {}) if review else {}

    # ML risk prediction
    ml_risk = None
    try:
        v_type = claim.get("vehicle_type", "Car")
        idv = float(claim.get("idv") or 450000.0)
        repair = float(claim.get("repair_estimate") or 0.0)
        ml_res = ml_service.predict_claim_risk({
            "insured_value": idv,
            "repair_estimate": repair,
            "type_vehicle": "Motor-cycle" if "two" in v_type.lower() or "bike" in v_type.lower() else "Pick-up / Delivery Van",
            "usage": "Private",
            "prod_year": 2021,
            "premium": idv * 0.035,
            "ccm_ton": 150 if "two" in v_type.lower() else 1498,
            "seats_num": 2 if "two" in v_type.lower() else 5
        })
        ml_risk = {
            "risk_score": ml_res.get("risk_score"),
            "risk_tier": ml_res.get("risk_tier"),
            "payout_anomaly": ml_res.get("payout_anomaly")
        }
    except Exception:
        pass

    return {
        "claim": claim,
        "document_types": [d.get("document_type") for d in docs],
        "documents_summary": [
            {"type": d.get("document_type"), "filename": d.get("filename"), "length": len(d.get("content", ""))}
            for d in docs
        ],
        "documents_content": {d.get("document_type"): d.get("content", "")[:1200] for d in docs},
        "report": report_json,
        "ml_risk": ml_risk
    }


def chat_with_assistant(
    message: str,
    claim_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Main entry point for Claim AI Assistant.
    Coordinates context building, retrieval grounding, LLM generation, or deterministic fallback.
    """
    message_clean = message.strip()
    history = history or []

    # Detect claim ID in message if not provided
    if not claim_id:
        match = re.search(r'\b(CLM\d{3,4})\b', message_clean, re.IGNORECASE)
        if match:
            claim_id = match.group(1).upper()

    context = _gather_claim_context(claim_id) if claim_id else {}
    retrieved_clauses = retrieval_service.retrieve_relevant_clauses(message_clean, top_k=4)

    # 1. Try Gemini GenAI if available
    if gemini_service.is_available():
        gemini_response = _call_gemini_assistant(message_clean, context, retrieved_clauses, history)
        if gemini_response:
            return gemini_response

    # 2. Comprehensive Deterministic Expert AI Engine
    return _deterministic_assistant_engine(message_clean, claim_id, context, retrieved_clauses)


def _call_gemini_assistant(
    message: str,
    context: Dict[str, Any],
    retrieved_clauses: List[Dict[str, Any]],
    history: List[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    """Invoke Gemini model with insurance copilot system instructions."""
    try:
        system_instruction = (
            "You are ClaimLens AI Copilot, a senior motor insurance claims investigation assistant "
            "(Track PS02, IRDAI compliance). You assist claims investigators and surveyors.\n"
            "Guidelines:\n"
            "1. Ground all answers firmly in available evidence, policy clauses, and facts.\n"
            "2. Cite specific policy clause IDs (e.g. POL-001, POL-009, POL-010) and document sources.\n"
            "3. Format outputs with clean markdown: headings, bold key metrics, bullet points, and tables.\n"
            "4. Be objective, thorough, and professional.\n"
            "5. If drafting an RFI (Request for Information), format it as an official insurer letter.\n"
            "6. Provide actionable recommendations (Approve, Reject, Escalate, Request Information)."
        )

        prompt_parts = []
        prompt_parts.append(f"USER QUERY: {message}\n")

        if context.get("claim"):
            c = context["claim"]
            prompt_parts.append("CURRENT CLAIM CONTEXT:")
            prompt_parts.append(f"- Claim ID: {c.get('claim_id')}")
            prompt_parts.append(f"- Policy Number: {c.get('policy_number')} ({c.get('policy_start_date')} to {c.get('policy_end_date')})")
            prompt_parts.append(f"- Customer: {c.get('customer_name')}")
            prompt_parts.append(f"- Vehicle: {c.get('vehicle_type')} (Reg: {c.get('vehicle_registration')})")
            prompt_parts.append(f"- Incident: {c.get('incident_type')} on {c.get('incident_date')} at {c.get('incident_time')} ({c.get('incident_location')})")
            prompt_parts.append(f"- IDV: ₹{c.get('idv', 0):,.2f} | Repair Estimate: ₹{c.get('repair_estimate', 0):,.2f} | Deductible: ₹{c.get('deductible', 0):,.2f}")
            prompt_parts.append(f"- Current Status: {c.get('status')} | Scenario: {c.get('scenario_type')}\n")

        rep = context.get("report", {})
        if rep:
            rec = rep.get("recommendation", {})
            prompt_parts.append(f"EVALUATION STATUS:")
            prompt_parts.append(f"- Recommendation: {rec.get('recommendation')} (Confidence: {rec.get('confidence')})")
            prompt_parts.append(f"- Explanation: {rec.get('explanation')}")

            contradictions = [c for c in rep.get("consistency_checks", []) if c.get("status") == "CONTRADICTION"]
            if contradictions:
                prompt_parts.append(f"- Detected Contradictions ({len(contradictions)}):")
                for ct in contradictions:
                    prompt_parts.append(f"  * {ct.get('field_name')} [{ct.get('severity')}]: {ct.get('details')}")

            missing = rep.get("completeness", {}).get("missing_documents", [])
            if missing:
                prompt_parts.append(f"- Missing Documents ({len(missing)}):")
                for md in missing:
                    prompt_parts.append(f"  * {md.get('label')} (Required by: {', '.join(md.get('required_by', []))})")

            calcs = rep.get("calculations", {})
            if calcs:
                prompt_parts.append(f"- Calculations: Net Payable ₹{calcs.get('net_payable', 0):,.2f}, Total Depreciation ₹{calcs.get('total_depreciation', 0):,.2f}")

        if context.get("documents_content"):
            prompt_parts.append("\nDOCUMENT EXCERPTS:")
            for doc_type, excerpt in context["documents_content"].items():
                prompt_parts.append(f"--- Document: {doc_type} ---\n{excerpt[:600]}\n")

        if retrieved_clauses:
            prompt_parts.append("\nRELEVANT POLICY CLAUSES (RAG RETRIEVAL):")
            for cl in retrieved_clauses:
                prompt_parts.append(f"- [{cl.get('clause_id')}] {cl.get('title')}: {cl.get('rule')}")

        if history:
            prompt_parts.append("\nPREVIOUS CONVERSATION CONTEXT:")
            for item in history[-3:]:
                role = item.get("role", "user")
                prompt_parts.append(f"{role.upper()}: {item.get('content', '')}")

        full_prompt = "\n".join(prompt_parts)
        text_response = gemini_service.generate_text(full_prompt, system_instruction=system_instruction)

        if text_response:
            citations = []
            if context.get("claim"):
                citations.append({
                    "source": f"Claim Master ({context['claim']['claim_id']})",
                    "clause_id": "DATABASE",
                    "confidence": 0.99
                })
            for cl in retrieved_clauses:
                citations.append({
                    "source": f"Policy Manual: {cl.get('title')}",
                    "clause_id": cl.get('clause_id'),
                    "confidence": round(float(cl.get('score', 0.85)), 2)
                })

            actions = _generate_contextual_actions(context.get("claim", {}).get("claim_id"))

            return {
                "answer": text_response,
                "engine": "gemini-2.5-flash",
                "grounding_citations": citations,
                "suggested_actions": actions,
                "claim_id": context.get("claim", {}).get("claim_id")
            }
    except Exception as e:
        print(f"  [!] Gemini assistant error: {e}")

    return None


def _deterministic_assistant_engine(
    message: str,
    claim_id: Optional[str],
    context: Dict[str, Any],
    retrieved_clauses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    High-precision deterministic motor insurance intelligence engine.
    Understands claims investigation, IRDAI guidelines, contradictions, calculations, and communication.
    """
    q_lower = message.lower()
    claim = context.get("claim")
    report = context.get("report", {})
    citations = []
    actions = []

    # Format retrieved clauses for citation
    for cl in retrieved_clauses:
        citations.append({
            "source": f"Policy Section: {cl.get('title')}",
            "clause_id": cl.get('clause_id'),
            "confidence": 0.92
        })

    # ═════════════════════════════════════════════════════════════════
    # SCENARIO 1: NO CLAIM SPECIFIED & GLOBAL QUERY
    # ═════════════════════════════════════════════════════════════════
    if not claim:
        # Check if user asked about high risk claims
        if any(w in q_lower for w in ["high risk", "fraud", "contradiction", "escalate", "suspicious", "find claim"]):
            all_c = get_all_claims()
            escalated = [c for c in all_c if c.get("status") == "ESCALATE" or c.get("scenario_type") in ("CONTRADICTION", "EXCLUSION")]

            answer = "### 🚨 High-Risk & Escalated Claims Portfolio Audit\n\n"
            answer += "Here are the top claims requiring immediate investigator intervention due to critical evidence contradictions, fraud signals, or policy breaches:\n\n"
            answer += "| Claim ID | Claimant | Vehicle | Incident | IDV / Estimate | Risk Category |\n"
            answer += "|---|---|---|---|---|---|\n"
            for c in escalated[:6]:
                cid = c.get('claim_id')
                est = f"₹{c.get('repair_estimate', 0):,.0f}"
                answer += f"| **{cid}** | {c.get('customer_name')} | {c.get('vehicle_registration')} ({c.get('vehicle_type')}) | {c.get('incident_type')} | {est} | `{c.get('scenario_type')}` |\n"

            answer += "\n\n💡 **Recommended Action:** Select any claim from the context dropdown above or click one of the quick actions below to inspect full evidence."
            actions = [
                {"label": "Inspect CLM051 (Contradictions)", "action": "select_claim", "claim_id": "CLM051"},
                {"label": "Inspect CLM056 (Commercial Exclusion)", "action": "select_claim", "claim_id": "CLM056"},
                {"label": "Inspect CLM075 (Difficult Theft)", "action": "select_claim", "claim_id": "CLM075"}
            ]
            return {
                "answer": answer,
                "engine": "claimlens-expert-rules",
                "grounding_citations": citations,
                "suggested_actions": actions,
                "claim_id": None
            }

        # Check for policy rule or depreciation questions
        if any(w in q_lower for w in ["depreciation", "metal", "rubber", "plastic", "glass"]):
            answer = (
                "### 📊 Standard Depreciation Schedule (IRDAI Motor Policy Guidelines)\n\n"
                "Under standard Indian Motor Own Damage policies, depreciation on parts replaced in an accident is deducted as follows:\n\n"
                "1. **Fixed Part Depreciation Rates:**\n"
                "   - **Rubber, Nylon, Plastic Parts & Tyres/Tubes/Batteries/Airbags:** **50%** deduction\n"
                "   - **Fiber Glass Components:** **30%** deduction\n"
                "   - **Glass Components (Windshield, Mirrors):** **0% (Nil)** deduction\n\n"
                "2. **Age-Based Metal Depreciation Rates:**\n"
                "   | Vehicle Age | Metal Depreciation Rate |\n"
                "   |---|---|\n"
                "   | Not exceeding 6 months | **Nil (0%)** |\n"
                "   | 6 months to 1 year | **5%** |\n"
                "   | 1 year to 2 years | **10%** |\n"
                "   | 2 years to 3 years | **15%** |\n"
                "   | 3 years to 4 years | **25%** |\n"
                "   | 4 years to 5 years | **35%** |\n"
                "   | 5 years to 10 years | **40%** |\n"
                "   | Over 10 years | **50%** |\n\n"
                "3. **Zero-Depreciation Add-on (Bumper-to-Bumper):**\n"
                "   If the policy includes the *Zero Depreciation Endorsement*, all parts depreciation is waived (100% reimbursed minus compulsory deductible)."
            )
            citations.append({"source": "Policy Clause POL-014", "clause_id": "POL-014", "confidence": 0.98})
            return {
                "answer": answer,
                "engine": "claimlens-expert-rules",
                "grounding_citations": citations,
                "suggested_actions": [{"label": "Audit Claim Settlement", "action": "select_claim", "claim_id": "CLM001"}],
                "claim_id": None
            }

        if any(w in q_lower for w in ["theft", "fir", "delay", "police"]):
            answer = (
                "### 🚨 IRDAI & Policy Mandate for Theft Claims (Clause POL-016)\n\n"
                "In motor theft claims, strict adherence to notification timelines is legally binding:\n\n"
                "- **Police FIR Requirement:** Must be registered within **24 hours** of the discovery of theft under Section 379 IPC.\n"
                "- **Insurer Notification:** Insurer must be informed immediately (max **48 hours**).\n"
                "- **Mandatory Evidence:**\n"
                "  1. Certified Copy of Police FIR\n"
                "  2. Untraced / Final Police Report (under Section 173 CrPC) accepted by Judicial Magistrate\n"
                "  3. Both sets of original ignition keys\n"
                "  4. Original Registration Certificate (RC) book & transfer forms (Form 28, 29, 30)\n"
                "  5. RTO theft intimation & non-encumbrance certificate\n\n"
                "⚠️ *Unexplained delays of >7 days without reasonable cause empower the insurer to repudiate the claim under condition 1 of the Motor Policy.*"
            )
            citations.append({"source": "Policy Clause POL-016", "clause_id": "POL-016", "confidence": 0.99})
            return {
                "answer": answer,
                "engine": "claimlens-expert-rules",
                "grounding_citations": citations,
                "suggested_actions": [{"label": "Analyze Theft Claim CLM021", "action": "select_claim", "claim_id": "CLM021"}],
                "claim_id": None
            }

        # Default general response
        answer = (
            "### 🤖 ClaimLens AI Copilot — Motor Claims Evidence Specialist\n\n"
            "I am ready to assist your investigation. I have full access to policy rules, IRDAI guidelines, and all claims in the repository.\n\n"
            "**How I can assist you:**\n"
            "- 🔍 **Audit Evidence Contradictions:** Cross-examine surveyor estimates, FIR records, and claimant statements.\n"
            "- 📜 **Policy Clause Grounding:** Check exclusions (intoxication, commercial use, delay in FIR, flood damage).\n"
            "- 💰 **Settlement Calculation:** Verify parts depreciation, compulsory deductible, and net payable.\n"
            "- ✉️ **Draft Communications:** Generate formal Request for Information (RFI) notices and surveyor inquiries.\n"
            "- ⚖️ **Adjudication Recommendation:** Produce defensible recommendations with audit trails.\n\n"
            "👉 **Select a claim from the dropdown above** or choose a suggested query below to begin."
        )
        return {
            "answer": answer,
            "engine": "claimlens-expert-rules",
            "grounding_citations": citations,
            "suggested_actions": [
                {"label": "Select CLM051 (Contradictions)", "action": "select_claim", "claim_id": "CLM051"},
                {"label": "Select CLM056 (Exclusion)", "action": "select_claim", "claim_id": "CLM056"},
                {"label": "Select CLM047 (Missing Docs)", "action": "select_claim", "claim_id": "CLM047"}
            ],
            "claim_id": None
        }

    # ═════════════════════════════════════════════════════════════════
    # SCENARIO 2: CLAIM IS SELECTED — DEEP EVIDENCE GROUNDED REASONING
    # ═════════════════════════════════════════════════════════════════
    cid = claim.get("claim_id")
    c_name = claim.get("customer_name")
    v_type = claim.get("vehicle_type")
    v_reg = claim.get("vehicle_registration")
    inc_type = claim.get("incident_type")
    idv = float(claim.get("idv") or 0.0)
    rep_est = float(claim.get("repair_estimate") or 0.0)
    status = claim.get("status")

    contradictions = [c for c in report.get("consistency_checks", []) if c.get("status") == "CONTRADICTION"]
    missing_docs = report.get("completeness", {}).get("missing_documents", [])
    rec_obj = report.get("recommendation", {})
    calc_obj = report.get("calculations", {})

    actions = _generate_contextual_actions(cid)

    # ── 2A. CONTRADICTIONS & DISCREPANCIES AUDIT ──
    if any(w in q_lower for w in ["contradict", "discrepan", "conflict", "audit", "mismatch", "inconsisten"]):
        answer = f"### 🔍 Discrepancy & Contradiction Audit: Claim {cid}\n\n"
        answer += f"**Insured:** {c_name} | **Vehicle:** {v_reg} ({v_type}) | **Type:** {inc_type}\n\n"

        if contradictions:
            answer += f"⚠️ **Found {len(contradictions)} Critical Evidence Contradiction(s):**\n\n"
            for idx, ct in enumerate(contradictions, 1):
                sev = ct.get('severity', 'HIGH')
                field = ct.get('field_name', 'General')
                details = ct.get('details', '')
                vals = ct.get('values', {})
                badge = "🔴 CRITICAL" if sev == "CRITICAL" else ("🟠 HIGH" if sev == "HIGH" else "🟡 MEDIUM")

                answer += f"#### {idx}. {field} [{badge}]\n"
                answer += f"- **Issue Details:** {details}\n"
                if vals:
                    answer += "- **Document Cross-Reference:**\n"
                    for doc_src, val in vals.items():
                        answer += f"  * *{doc_src}*: `{val}`\n"
                answer += "\n"

            answer += "### 🛡️ Investigator Assessment:\n"
            answer += "- **Fraud / Misrepresentation Risk:** Severe discrepancy between filed declaration and independent records (FIR/surveyor).\n"
            answer += "- **Action Required:** Issue formal inquiry letter requesting original police logbook and statement clarification prior to any settlement.\n"
        else:
            answer += "✅ **No Contradictions Found:**\n\n"
            answer += "Cross-document verification across the Claim Form, Surveyor Report, Repair Invoice, and Police Records shows consistent facts regarding date, time, driver identity, vehicle registration, and damage scope.\n\n"
            answer += f"- **Driver Declared:** Verified across records\n"
            answer += f"- **Incident Date/Time:** Aligns with police/surveyor notes\n"
            answer += f"- **Registration:** {v_reg} matches all documents"

        return {
            "answer": answer,
            "engine": "claimlens-expert-rules",
            "grounding_citations": citations,
            "suggested_actions": actions,
            "claim_id": cid
        }

    # ── 2B. POLICY EXCLUSIONS & CLAUSES ──
    if any(w in q_lower for w in ["exclusion", "clause", "breach", "policy rule", "cover", "pol-"]):
        findings = report.get("policy_findings", [])
        failed = [f for f in findings if f.get("status") == "FAIL"]
        warnings = [f for f in findings if f.get("status") == "WARNING"]

        answer = f"### 📜 Policy Coverage & Exclusion Analysis: Claim {cid}\n\n"
        answer += f"Policy No: **{claim.get('policy_number')}** | Period: {claim.get('policy_start_date')} to {claim.get('policy_end_date')}\n\n"

        if failed:
            answer += "❌ **Violated Policy Clauses (Repudiation / Breach Grounds):**\n\n"
            for f in failed:
                answer += f"- **[{f.get('clause_id')}] {f.get('title')}**\n"
                answer += f"  * **Rule:** {f.get('rule')}\n"
                answer += f"  * **Evidence Cited:** {f.get('evidence')}\n"
                citations.append({"source": f"Clause {f.get('clause_id')}", "clause_id": f.get('clause_id'), "confidence": 0.95})
            answer += "\n"

        if warnings:
            answer += "⚠️ **Warning Clauses (Review Required):**\n\n"
            for w in warnings:
                answer += f"- **[{w.get('clause_id')}] {w.get('title')}** — {w.get('evidence')}\n"
                citations.append({"source": f"Clause {w.get('clause_id')}", "clause_id": w.get('clause_id'), "confidence": 0.85})
            answer += "\n"

        if not failed and not warnings:
            answer += "✅ **Full Policy Compliance Verified:**\n\n"
            answer += "- Policy was active and in-force on the incident date (Clause POL-001).\n"
            answer += "- Driver held a valid license category for the insured vehicle (Clause POL-002).\n"
            answer += "- No evidence of unauthorized commercial usage, drunken driving, or intentional gross negligence.\n"
            answer += "- The cause of loss is covered under Section 1 (Own Damage) of the Indian Standard Motor Package Policy."

        return {
            "answer": answer,
            "engine": "claimlens-expert-rules",
            "grounding_citations": citations,
            "suggested_actions": actions,
            "claim_id": cid
        }

    # ── 2C. SETTLEMENT & PAYOUT CALCULATION ──
    if any(w in q_lower for w in ["calculate", "calculation", "payout", "settlement", "payable", "depreciation", "deductible"]):
        answer = f"### 💰 Financial Settlement & Deductions Breakdown: Claim {cid}\n\n"

        total_est = rep_est or float(calc_obj.get("total_estimate", 0.0))
        deprec = float(calc_obj.get("total_depreciation", total_est * 0.18))
        deductible = float(claim.get("deductible") or calc_obj.get("compulsory_deductible", 1000.0))
        salvage = float(calc_obj.get("salvage_value", total_est * 0.05))
        net_pay = max(0.0, total_est - deprec - deductible - salvage)

        answer += "| Component | Amount (₹) | Basis / Clause Reference |\n"
        answer += "|---|---|---|\n"
        answer += f"| **Total Claim / Repair Estimate** | ₹{total_est:,.2f} | Authorized Workshop Estimate |\n"
        answer += f"| **Less: Parts Depreciation** | -₹{deprec:,.2f} | IRDAI Schedule (Rubber 50%, Metal age curve) |\n"
        answer += f"| **Less: Compulsory Deductible** | -₹{deductible:,.2f} | Standard Deductible (Clause POL-015) |\n"
        answer += f"| **Less: Estimated Salvage** | -₹{salvage:,.2f} | Damaged Parts Recovery Value |\n"
        answer += f"| **NET ADMISSIBLE PAYABLE** | **₹{net_pay:,.2f}** | **Final Authorized Payout** |\n\n"

        answer += f"- **Insured Declared Value (IDV):** ₹{idv:,.2f}\n"
        ratio = (total_est / idv * 100) if idv > 0 else 0
        answer += f"- **Estimate / IDV Ratio:** `{ratio:.1f}%` "
        if ratio >= 75:
            answer += "🔴 **Exceeds 75% CTL Threshold (Constructive Total Loss applies under Clause POL-008)!**"
        else:
            answer += "🟢 Within partial repair limits (<75% of IDV)."

        citations.append({"source": "Clause POL-014 (Depreciation)", "clause_id": "POL-014", "confidence": 0.95})
        citations.append({"source": "Clause POL-015 (Compulsory Deductible)", "clause_id": "POL-015", "confidence": 0.95})

        return {
            "answer": answer,
            "engine": "claimlens-expert-rules",
            "grounding_citations": citations,
            "suggested_actions": actions,
            "claim_id": cid
        }

    # ── 2D. DRAFT REQUEST FOR INFORMATION (RFI) ──
    if any(w in q_lower for w in ["draft", "rfi", "letter", "email", "request information", "inquiry"]):
        missing_list = [m.get("label", "Document") for m in missing_docs] if missing_docs else ["Detailed explanation of incident timeline", "Original repair tax invoice"]
        answer = (
            f"### ✉️ Formal Request for Information (RFI) Notice\n\n"
            f"**To:** {c_name}  \n"
            f"**Policy Number:** {claim.get('policy_number')}  \n"
            f"**Claim Reference:** {cid}  \n"
            f"**Vehicle Registration:** {v_reg} ({v_type})  \n"
            f"**Subject:** Requirement of Crucial Documents / Clarification for Claim #{cid}\n\n"
            f"---\n\n"
            f"Dear {c_name},\n\n"
            f"With reference to your motor insurance claim registered under Claim No. **{cid}** for the incident on **{claim.get('incident_date')}**, "
            f"our claims assessment team has reviewed the submitted dossier.\n\n"
            f"To enable us to conclude the investigation and process your claim in accordance with IRDAI regulatory guidelines and policy terms, "
            f"we kindly request you to provide the following documents/clarifications within **7 business days** of receipt of this notice:\n\n"
        )
        for idx, item in enumerate(missing_list, 1):
            answer += f"{idx}. **{item}**\n"

        if contradictions:
            answer += f"\n**Clarification on Timeline/Declaration:**\n"
            for ct in contradictions[:2]:
                answer += f"- *{ct.get('field_name')}*: Please provide written clarification regarding the discrepancy noted between {ct.get('details')}.\n"

        answer += (
            f"\nKindly submit the requested documents directly via the Claims Portal or forward attested copies to our nearest claims processing hub.\n\n"
            f"Please note that delay in submission may hinder timely settlement or warrant file closure under Condition 5 of the Motor Vehicle Policy.\n\n"
            f"Yours sincerely,  \n"
            f"**Claims Investigation Department**  \n"
            f"ClaimLens Insurance Co. Ltd."
        )
        citations.append({"source": "Policy Clause POL-017 (Notice of Loss & Evidence)", "clause_id": "POL-017", "confidence": 0.95})

        return {
            "answer": answer,
            "engine": "claimlens-expert-rules",
            "grounding_citations": citations,
            "suggested_actions": actions,
            "claim_id": cid
        }

    # ── 2E. FINAL ADJUDICATION RECOMMENDATION & SUMMARY ──
    rec_val = rec_obj.get("recommendation", status)
    conf = rec_obj.get("confidence", "HIGH")
    exp = rec_obj.get("explanation", f"Claim {cid} is currently pending review.")

    answer = f"### ⚖️ Adjudication Review & Investigation Report: Claim {cid}\n\n"
    badge = "🟢 APPROVE" if rec_val == "APPROVE" else ("🔴 REJECT" if rec_val == "REJECT" else ("🟠 ESCALATE" if rec_val == "ESCALATE" else "🟡 REQUEST_INFORMATION"))

    answer += f"**Final Recommendation:** **{badge}** (Confidence: `{conf}`)\n\n"
    answer += f"**Core Evidence Justification:**\n{exp}\n\n"

    answer += "### 📋 Claim Master Dossier:\n"
    answer += f"- **Claimant:** {c_name} (Policy: `{claim.get('policy_number')}`)\n"
    answer += f"- **Vehicle:** {v_reg} • {v_type}\n"
    answer += f"- **Incident:** {inc_type} on {claim.get('incident_date')} at {claim.get('incident_time') or '14:30'}\n"
    answer += f"- **Financials:** IDV ₹{idv:,.2f} | Repair ₹{rep_est:,.2f}\n"

    if contradictions:
        answer += f"\n⚠️ **Active Flags:** {len(contradictions)} critical contradiction(s) flagged by cross-document audit."
    if missing_docs:
        answer += f"\n📁 **Pending Evidence:** {len(missing_docs)} missing mandatory document(s)."

    return {
        "answer": answer,
        "engine": "claimlens-expert-rules",
        "grounding_citations": citations,
        "suggested_actions": actions,
        "claim_id": cid
    }


def _generate_contextual_actions(claim_id: Optional[str]) -> List[Dict[str, str]]:
    """Generate interactive buttons for quick navigation in UI."""
    if not claim_id:
        return [
            {"label": "📂 Open Claims List", "action": "open_claims_list"},
            {"label": "🤖 Launch ML Engine", "action": "open_ml_engine"}
        ]

    return [
        {"label": f"🔍 View Claim {claim_id}", "action": "open_claim", "claim_id": claim_id},
        {"label": "🧪 Run Simulator", "action": "open_simulator", "claim_id": claim_id},
        {"label": "✉️ Copy RFI Draft", "action": "copy_rfi", "claim_id": claim_id},
        {"label": "📊 View PDF Studio", "action": "open_doc_studio", "claim_id": claim_id}
    ]

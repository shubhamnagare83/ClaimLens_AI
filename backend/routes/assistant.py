"""
ClaimLens AI — Assistant Router
Endpoints for Claim AI Assistant Copilot
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.models import AssistantChatRequest
from backend.services import assistant_service

router = APIRouter()


@router.post("/api/assistant/chat")
async def assistant_chat(req: AssistantChatRequest):
    """Handle conversational queries grounded in claim evidence & policy clauses."""
    try:
        response = assistant_service.chat_with_assistant(
            message=req.message,
            claim_id=req.claim_id,
            history=req.history
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Assistant processing failed: {str(e)}")


@router.get("/api/assistant/suggestions")
async def get_suggestions(claim_id: Optional[str] = Query(None)):
    """Return tailored suggestion prompt pills based on selected claim."""
    suggestions = assistant_service.get_suggested_prompts(claim_id)
    return {"suggestions": suggestions}


@router.get("/api/assistant/claims")
async def get_assistant_claims():
    """Return quick claim list for the assistant selector."""
    claims = assistant_service.get_all_claims_summary()
    return {"claims": claims}

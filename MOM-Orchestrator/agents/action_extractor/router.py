"""
Action Extractor Agent Router
Individual testing endpoint for action extractor agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from .agent import ActionExtractorAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/action-extractor", tags=["Agent Testing"])


class ActionTestRequest(BaseModel):
    transcript: str


class ActionTestResponse(BaseModel):
    status: str
    actions: List[Dict[str, Any]]
    confidence: float
    reasoning: str


@router.post("/", response_model=ActionTestResponse)
async def test_action_extractor(request: ActionTestRequest):
    """Test action extractor with transcript"""
    agent = ActionExtractorAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="extract_actions",
        payload=Payload(input_type="text", content=request.transcript),
        context=Context(
            conversation_history=[],
            intermediate_data={"english_transcript": request.transcript},
            memory={},
        ),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return ActionTestResponse(
        status=response.status,
        actions=response.data.output.get("actions", []),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

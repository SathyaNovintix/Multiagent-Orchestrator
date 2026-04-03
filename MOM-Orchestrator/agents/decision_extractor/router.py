"""
Decision Extractor Agent Router
Individual testing endpoint for decision extractor agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from .agent import DecisionExtractorAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/decision-extractor", tags=["Agent Testing"])


class DecisionTestRequest(BaseModel):
    transcript: str


class DecisionTestResponse(BaseModel):
    status: str
    decisions: List[Dict[str, Any]]
    confidence: float
    reasoning: str


@router.post("/", response_model=DecisionTestResponse)
async def test_decision_extractor(request: DecisionTestRequest):
    """Test decision extractor with transcript"""
    agent = DecisionExtractorAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="extract_decisions",
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
    
    return DecisionTestResponse(
        status=response.status,
        decisions=response.data.output.get("decisions", []),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

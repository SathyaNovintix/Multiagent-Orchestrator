"""
Formatter Agent Router
Individual testing endpoint for formatter agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .agent import FormatterAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/formatter", tags=["Agent Testing"])


class FormatterTestRequest(BaseModel):
    topics: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    format_id: Optional[str] = "standard"


class FormatterTestResponse(BaseModel):
    status: str
    structured_mom: Dict[str, Any]
    confidence: float
    reasoning: str


@router.post("/", response_model=FormatterTestResponse)
async def test_formatter(request: FormatterTestRequest):
    """Test formatter with meeting data"""
    agent = FormatterAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="format_mom",
        payload=Payload(input_type="text", content=""),
        context=Context(
            conversation_history=[],
            intermediate_data={
                "topics": request.topics,
                "decisions": request.decisions,
                "actions": request.actions,
                "format_id": request.format_id,
            },
            memory={},
        ),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return FormatterTestResponse(
        status=response.status,
        structured_mom=response.data.output.get("structured_mom", {}),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

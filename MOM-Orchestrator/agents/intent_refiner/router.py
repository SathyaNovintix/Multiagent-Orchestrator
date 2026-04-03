"""
Intent Refiner Agent Router
Individual testing endpoint for intent refiner agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .agent import IntentRefinerAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/intent-refiner", tags=["Agent Testing"])


class IntentTestRequest(BaseModel):
    text: str
    current_intent: str = "auto_detect"


class IntentTestResponse(BaseModel):
    status: str
    detected_intent: str
    confidence: float
    reasoning: str


@router.post("/", response_model=IntentTestResponse)
async def test_intent_refiner(request: IntentTestRequest):
    """Test intent refiner with text input"""
    agent = IntentRefinerAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent=request.current_intent,
        payload=Payload(input_type="text", content=request.text),
        context=Context(conversation_history=[], intermediate_data={}, memory={}),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return IntentTestResponse(
        status=response.status,
        detected_intent=response.intent or request.current_intent,
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

"""
Conversational Agent Router
Individual testing endpoint for conversational agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .agent import ConversationalAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/conversational", tags=["Agent Testing"])


class ConversationalTestRequest(BaseModel):
    user_input: str
    conversation_history: Optional[List[Dict[str, Any]]] = []
    meeting_context: Optional[Dict[str, Any]] = {}


class ConversationalTestResponse(BaseModel):
    status: str
    user_message: str
    reasoning: str
    confidence: float


@router.post("/", response_model=ConversationalTestResponse)
async def test_conversational_agent(request: ConversationalTestRequest):
    """Test conversational agent with user input"""
    agent = ConversationalAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="chat",
        payload=Payload(input_type="text", content=request.user_input),
        context=Context(
            conversation_history=request.conversation_history,
            intermediate_data=request.meeting_context,
            memory={},
        ),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return ConversationalTestResponse(
        status=response.status,
        user_message=response.data.output.get("user_message", ""),
        reasoning=response.reasoning,
        confidence=response.data.confidence,
    )

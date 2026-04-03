"""
Response Generator Agent Router
Individual testing endpoint for response generator agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from .agent import ResponseGeneratorAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/response-generator", tags=["Agent Testing"])


class ResponseGenTestRequest(BaseModel):
    structured_mom: Dict[str, Any]
    file_url: Optional[str] = None


class ResponseGenTestResponse(BaseModel):
    status: str
    user_message: str
    file_url: Optional[str]
    confidence: float
    reasoning: str


@router.post("/", response_model=ResponseGenTestResponse)
async def test_response_generator(request: ResponseGenTestRequest):
    """Test response generator with MOM data"""
    agent = ResponseGeneratorAgent()
    
    intermediate_data = {"structured_mom": request.structured_mom}
    if request.file_url:
        intermediate_data["file_url"] = request.file_url
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="generate_response",
        payload=Payload(input_type="text", content=""),
        context=Context(
            conversation_history=[],
            intermediate_data=intermediate_data,
            memory={},
        ),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return ResponseGenTestResponse(
        status=response.status,
        user_message=response.data.output.get("user_message", ""),
        file_url=response.data.output.get("file_url"),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

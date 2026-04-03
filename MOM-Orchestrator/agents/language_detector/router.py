"""
Language Detector Agent Router
Individual testing endpoint for language detector agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .agent import LanguageDetectorAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/language-detector", tags=["Agent Testing"])


class LanguageTestRequest(BaseModel):
    text: str


class LanguageTestResponse(BaseModel):
    status: str
    detected_language: str
    language_confidence: float
    reasoning: str


@router.post("/", response_model=LanguageTestResponse)
async def test_language_detector(request: LanguageTestRequest):
    """Test language detector with text input"""
    agent = LanguageDetectorAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="detect_language",
        payload=Payload(input_type="text", content=request.text),
        context=Context(conversation_history=[], intermediate_data={}, memory={}),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return LanguageTestResponse(
        status=response.status,
        detected_language=response.data.output.get("detected_language", "unknown"),
        language_confidence=response.data.output.get("language_confidence", 0.0),
        reasoning=response.reasoning,
    )

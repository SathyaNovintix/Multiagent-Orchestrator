"""
Translator Agent Router
Individual testing endpoint for translator agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .agent import TranslatorAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/translator", tags=["Agent Testing"])


class TranslatorTestRequest(BaseModel):
    text: str
    source_language: Optional[str] = "auto"


class TranslatorTestResponse(BaseModel):
    status: str
    english_transcript: str
    confidence: float
    reasoning: str


@router.post("/", response_model=TranslatorTestResponse)
async def test_translator(request: TranslatorTestRequest):
    """Test translator with text input"""
    agent = TranslatorAgent()
    
    intermediate_data = {}
    if request.source_language != "auto":
        intermediate_data["detected_language"] = request.source_language
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="translate",
        payload=Payload(input_type="text", content=request.text),
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
    
    return TranslatorTestResponse(
        status=response.status,
        english_transcript=response.data.output.get("english_transcript", ""),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

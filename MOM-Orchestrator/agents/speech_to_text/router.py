"""
Speech to Text Agent Router
Individual testing endpoint for speech to text agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .agent import SpeechToTextAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/speech-to-text", tags=["Agent Testing"])


class SpeechToTextTestRequest(BaseModel):
    audio_url: str
    language_hint: Optional[str] = None


class SpeechToTextTestResponse(BaseModel):
    status: str
    transcript: str
    confidence: float
    reasoning: str


@router.post("/", response_model=SpeechToTextTestResponse)
async def test_speech_to_text(request: SpeechToTextTestRequest):
    """Test speech to text with audio URL"""
    agent = SpeechToTextAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="transcribe_audio",
        payload=Payload(
            input_type="audio",
            content=request.audio_url,
            language=request.language_hint,
        ),
        context=Context(
            conversation_history=[],
            intermediate_data={},
            memory={},
        ),
        meta=Meta(source="test_router"),
    )
    
    response = await agent.run(agent_request)
    
    if response.status == "fail":
        raise HTTPException(status_code=500, detail=response.reasoning)
    
    return SpeechToTextTestResponse(
        status=response.status,
        transcript=response.data.output.get("transcript", ""),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

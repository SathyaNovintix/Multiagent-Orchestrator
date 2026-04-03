"""
Topic Extractor Agent Router
Individual testing endpoint for topic extractor agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from .agent import TopicExtractorAgent
from schemas.contracts import AgentRequest, Payload, Context, Meta

router = APIRouter(prefix="/test/topic-extractor", tags=["Agent Testing"])


class TopicTestRequest(BaseModel):
    transcript: str


class TopicTestResponse(BaseModel):
    status: str
    topics: List[Dict[str, Any]]
    confidence: float
    reasoning: str


@router.post("/", response_model=TopicTestResponse)
async def test_topic_extractor(request: TopicTestRequest):
    """Test topic extractor with transcript"""
    agent = TopicExtractorAgent()
    
    agent_request = AgentRequest(
        session_id="test-session",
        intent="extract_topics",
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
    
    return TopicTestResponse(
        status=response.status,
        topics=response.data.output.get("topics", []),
        confidence=response.data.confidence,
        reasoning=response.reasoning,
    )

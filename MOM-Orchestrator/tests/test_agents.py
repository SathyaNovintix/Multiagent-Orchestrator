"""
Unit tests for individual agents.
LLM calls are stubbed via conftest.py.
Redis calls are in-memory via conftest.py.
"""
import pytest
from schemas.contracts import AgentRequest, Payload, Context, Meta
from tests.conftest import SAMPLE_TRANSCRIPT


def make_request(content: str, input_type: str = "text", intent: str = "generate_mom",
                 intermediate: dict = None) -> AgentRequest:
    return AgentRequest(
        session_id="test-session",
        intent=intent,
        payload=Payload(input_type=input_type, content=content),
        context=Context(intermediate_data=intermediate or {}),
        meta=Meta(source="orchestrator"),
    )


@pytest.mark.asyncio
async def test_language_detector_english():
    from agents.language_detector import LanguageDetectorAgent
    agent = LanguageDetectorAgent()
    req = make_request("This is a clear English sentence for testing purposes.")
    resp = await agent.run(req)
    assert resp.status == "success"
    assert resp.data.output["detected_language"] == "en"
    assert resp.data.output["language_confidence"] > 0.5


@pytest.mark.asyncio
async def test_language_detector_short_text_fails():
    from agents.language_detector import LanguageDetectorAgent
    agent = LanguageDetectorAgent()
    req = make_request("hi")
    resp = await agent.run(req)
    assert resp.status == "fail"


@pytest.mark.asyncio
async def test_intent_refiner_returns_generate_mom():
    from agents.intent_refiner import IntentRefinerAgent
    agent = IntentRefinerAgent()
    req = make_request(SAMPLE_TRANSCRIPT, intent="auto_detect")
    resp = await agent.run(req)
    assert resp.status == "success"
    assert resp.intent == "generate_mom"
    assert resp.data.confidence > 0.9


@pytest.mark.asyncio
async def test_topic_extractor_returns_topics():
    from agents.topic_extractor import TopicExtractorAgent
    agent = TopicExtractorAgent()
    req = make_request(SAMPLE_TRANSCRIPT, intermediate={"english_transcript": SAMPLE_TRANSCRIPT})
    resp = await agent.run(req)
    assert resp.status == "success"
    topics = resp.data.output.get("topics", [])
    assert len(topics) >= 1
    assert "title" in topics[0]


@pytest.mark.asyncio
async def test_decision_extractor_returns_decisions():
    from agents.decision_extractor import DecisionExtractorAgent
    agent = DecisionExtractorAgent()
    req = make_request(SAMPLE_TRANSCRIPT, intermediate={"english_transcript": SAMPLE_TRANSCRIPT})
    resp = await agent.run(req)
    assert resp.status == "success"
    decisions = resp.data.output.get("decisions", [])
    assert len(decisions) >= 1


@pytest.mark.asyncio
async def test_action_extractor_returns_actions():
    from agents.action_extractor import ActionExtractorAgent
    agent = ActionExtractorAgent()
    req = make_request(SAMPLE_TRANSCRIPT, intermediate={"english_transcript": SAMPLE_TRANSCRIPT})
    resp = await agent.run(req)
    assert resp.status == "success"
    actions = resp.data.output.get("actions", [])
    assert len(actions) >= 1
    assert "task" in actions[0]
    assert "owner" in actions[0]


@pytest.mark.asyncio
async def test_formatter_builds_structured_mom():
    from agents.formatter import FormatterAgent
    from unittest.mock import AsyncMock, patch

    agent = FormatterAgent()
    req = make_request(
        SAMPLE_TRANSCRIPT,
        intermediate={
            "topics": [{"title": "T1", "summary": "S1", "timestamp": None}],
            "decisions": [{"decision": "D1", "owner": "Alice", "condition": None}],
            "actions": [{"task": "A1", "owner": "Bob", "deadline": None, "priority": "high", "ambiguous": False}],
            "detected_language": "en",
        },
    )

    with patch("pdf.generator.generate_pdf", new_callable=AsyncMock) as mock_pdf:
        mock_pdf.return_value = "/tmp/test.pdf"
        resp = await agent.run(req)

    assert resp.status == "success"
    mom = resp.data.output.get("structured_mom", {})
    assert len(mom["topics"]) == 1
    assert len(mom["decisions"]) == 1
    assert len(mom["actions"]) == 1


@pytest.mark.asyncio
async def test_response_generator_formats_message():
    from agents.response_generator import ResponseGeneratorAgent
    agent = ResponseGeneratorAgent()
    req = make_request(
        "",
        intermediate={
            "structured_mom": {
                "mom_id": "m1",
                "topics": [{"title": "T1", "summary": "S1"}],
                "decisions": [{"decision": "D1", "owner": "Alice"}],
                "actions": [{"task": "A1", "owner": "Bob", "priority": "high", "ambiguous": False}],
                "original_language": "en",
                "file_url": "/api/mom/m1/download",
            },
            "file_url": "/api/mom/m1/download",
        },
    )
    resp = await agent.run(req)
    assert resp.status == "success"
    msg = resp.data.output.get("user_message", "")
    assert "1 Topic" in msg or "Topics" in msg

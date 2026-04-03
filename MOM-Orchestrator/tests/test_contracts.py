"""
Tests for the Universal Message Contract (Pydantic schemas).
"""
import pytest
from schemas.contracts import (
    AgentRequest, AgentResponse, Session, MOMDocument,
    Payload, Context, Meta, ResponseData, ResponseMeta,
)


def test_agent_request_minimal():
    req = AgentRequest(
        session_id="sess-1",
        intent="generate_mom",
        payload=Payload(input_type="text", content="hello"),
        meta=Meta(source="user"),
    )
    assert req.session_id == "sess-1"
    assert req.context.conversation_history == []


def test_agent_response_status_values():
    for status in ("success", "fail", "need_more_input", "route"):
        resp = AgentResponse(
            session_id="s",
            status=status,
            meta=ResponseMeta(agent="test_agent"),
        )
        assert resp.status == status


def test_agent_response_confidence_bounds():
    with pytest.raises(Exception):
        AgentResponse(
            session_id="s",
            status="success",
            data=ResponseData(output={}, confidence=1.5),  # > 1.0 — invalid
            meta=ResponseMeta(agent="test_agent"),
        )


def test_session_defaults():
    s = Session()
    assert s.status == "active"
    assert s.session_id != ""
    assert s.conversation_history == []


def test_mom_document_empty():
    mom = MOMDocument(session_id="s")
    assert mom.topics == []
    assert mom.decisions == []
    assert mom.actions == []
    assert mom.mom_id != ""

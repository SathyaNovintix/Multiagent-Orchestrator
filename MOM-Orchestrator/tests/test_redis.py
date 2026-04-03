"""
Tests for Redis session and MOM storage.
"""
import pytest
from schemas.contracts import Session, MOMDocument
from storage.redis_client import (
    create_session, get_session, update_session, delete_session,
    save_mom, get_mom, get_moms_for_session,
)


@pytest.mark.asyncio
async def test_create_and_get_session():
    session = Session(intent="generate_mom")
    await create_session(session)
    fetched = await get_session(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id
    assert fetched.intent == "generate_mom"


@pytest.mark.asyncio
async def test_update_session():
    session = Session()
    await create_session(session)
    session.status = "completed"
    session.intermediate_data = {"key": "value"}
    await update_session(session)

    fetched = await get_session(session.session_id)
    assert fetched.status == "completed"
    assert fetched.intermediate_data["key"] == "value"


@pytest.mark.asyncio
async def test_delete_session():
    session = Session()
    await create_session(session)
    await delete_session(session.session_id)
    fetched = await get_session(session.session_id)
    assert fetched is None


@pytest.mark.asyncio
async def test_session_not_found():
    result = await get_session("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_save_and_get_mom():
    mom = MOMDocument(
        session_id="sess-123",
        topics=[{"title": "T", "summary": "S", "timestamp": None}],
        decisions=[{"decision": "D", "owner": "Alice", "condition": None}],
        actions=[{"task": "A", "owner": "Bob", "deadline": None, "priority": "high"}],
        original_language="en",
    )
    await save_mom(mom)

    fetched = await get_mom(mom.mom_id)
    assert fetched is not None
    assert fetched.session_id == "sess-123"
    assert len(fetched.topics) == 1


@pytest.mark.asyncio
async def test_get_moms_for_session():
    sid = "sess-multi"
    mom1 = MOMDocument(session_id=sid, original_language="en")
    mom2 = MOMDocument(session_id=sid, original_language="ta")
    await save_mom(mom1)
    await save_mom(mom2)

    moms = await get_moms_for_session(sid)
    assert len(moms) == 2

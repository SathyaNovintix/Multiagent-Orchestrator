"""
Pytest configuration for AgentMesh AI tests.
Sets up a fake Redis, stubs the LLM, and provides common fixtures.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Fake Redis (in-memory dict)
# ---------------------------------------------------------------------------

class FakeRedis:
    """Minimal async Redis stand-in for testing."""

    def __init__(self):
        self._store: dict = {}
        self._sets: dict = {}
        self._ttls: dict = {}

    async def setex(self, key, ttl, value):
        self._store[key] = value
        self._ttls[key] = ttl

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)

    async def sadd(self, key, *members):
        self._sets.setdefault(key, set()).update(members)

    async def smembers(self, key):
        return self._sets.get(key, set())

    async def expire(self, key, ttl):
        self._ttls[key] = ttl


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace the global Redis client with an in-memory fake for all tests."""
    import storage.redis_client as rc
    fake = FakeRedis()
    rc._redis = fake
    return fake


# ---------------------------------------------------------------------------
# Stub LLM (avoid real Bedrock calls in tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    """Replace Bedrock LLM calls with deterministic stubs."""
    import llm.bedrock_client as bc

    async def fake_invoke_llm_json(system_prompt: str, user_prompt: str) -> dict:
        if "intent" in system_prompt.lower():
            return {"intent": "generate_mom", "confidence": 0.96, "reasoning": "stub"}
        if "topics" in system_prompt.lower():
            return {"topics": [{"title": "Test Topic", "summary": "Summary.", "timestamp": None}]}
        if "decisions" in system_prompt.lower():
            return {"decisions": [{"decision": "Test decision", "owner": "Team", "condition": None}]}
        if "actions" in system_prompt.lower():
            return {"actions": [{"task": "Test action", "owner": "Alice", "deadline": None, "priority": "high", "ambiguous": False}]}
        return {}

    monkeypatch.setattr(bc, "invoke_llm_json", fake_invoke_llm_json)


# ---------------------------------------------------------------------------
# Common test transcript
# ---------------------------------------------------------------------------

SAMPLE_TRANSCRIPT = """
Meeting: Q2 Planning
Attendees: Alice, Bob, Carol

Alice: We need to finalize the product roadmap by end of this week.
Bob: Agreed. The mobile app should be the priority. I'll own the mobile spec.
Carol: We also need to decide on the backend architecture.
Alice: Let's go with microservices. That's decided.
Bob: I'll set up the CI/CD pipeline by Friday.
Carol: I'll write the API docs by next Monday.
"""

"""
Redis Storage Layer — AgentMesh AI
Single source of truth for all session and MOM data.
No PostgreSQL — Redis only.
"""
import json
import os
from typing import Optional
import redis.asyncio as aioredis

from schemas.contracts import Session, MOMDocument

# TTL: 90 days (per NFR)
SESSION_TTL_SECONDS = 90 * 24 * 60 * 60

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis


# ---------------------------------------------------------------------------
# Session operations
# ---------------------------------------------------------------------------

def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def create_session(session: Session) -> Session:
    r = await get_redis()
    await r.setex(
        _session_key(session.session_id),
        SESSION_TTL_SECONDS,
        session.model_dump_json(),
    )
    return session


async def get_session(session_id: str) -> Optional[Session]:
    r = await get_redis()
    data = await r.get(_session_key(session_id))
    if data is None:
        return None
    return Session.model_validate_json(data)


async def update_session(session: Session) -> Session:
    from datetime import datetime
    session.updated_at = datetime.utcnow().isoformat() + "Z"
    r = await get_redis()
    # Refresh TTL on every update
    await r.setex(
        _session_key(session.session_id),
        SESSION_TTL_SECONDS,
        session.model_dump_json(),
    )
    return session


async def delete_session(session_id: str) -> None:
    r = await get_redis()
    await r.delete(_session_key(session_id))


# ---------------------------------------------------------------------------
# MOM Document operations
# ---------------------------------------------------------------------------

def _mom_key(mom_id: str) -> str:
    return f"mom:{mom_id}"


def _session_mom_index_key(session_id: str) -> str:
    return f"session_moms:{session_id}"


async def save_mom(mom: MOMDocument) -> MOMDocument:
    r = await get_redis()
    await r.setex(_mom_key(mom.mom_id), SESSION_TTL_SECONDS, mom.model_dump_json())
    # Index: track which MOMs belong to a session
    await r.sadd(_session_mom_index_key(mom.session_id), mom.mom_id)
    await r.expire(_session_mom_index_key(mom.session_id), SESSION_TTL_SECONDS)
    return mom


async def get_mom(mom_id: str) -> Optional[MOMDocument]:
    r = await get_redis()
    data = await r.get(_mom_key(mom_id))
    if data is None:
        return None
    return MOMDocument.model_validate_json(data)


async def get_moms_for_session(session_id: str) -> list[MOMDocument]:
    r = await get_redis()
    mom_ids = await r.smembers(_session_mom_index_key(session_id))
    moms = []
    for mom_id in mom_ids:
        mom = await get_mom(mom_id)
        if mom:
            moms.append(mom)
    return moms

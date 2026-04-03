"""
MongoDB Storage Layer — AgentMesh AI
Persistent storage for sessions, MOM documents, and chat messages.
Replaces Redis as the primary persistence layer.
Includes GridFS for audio file storage.
"""
from __future__ import annotations
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pymongo import ASCENDING, DESCENDING

from schemas.contracts import Session, MOMDocument

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME   = os.getenv("MONGODB_DB",  "agentmesh")

_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
    return _client


def get_db():
    return get_mongo_client()[DB_NAME]


async def ensure_indexes() -> None:
    """Create indexes on startup — idempotent."""
    db = get_db()
    await db["Orchestrator"].create_index([("session_id", ASCENDING)], unique=True)
    await db["Orchestrator"].create_index([("created_at", DESCENDING)])
    await db["moms"].create_index([("mom_id", ASCENDING)], unique=True)
    await db["moms"].create_index([("session_id", ASCENDING)])
    await db["messages"].create_index([("session_id", ASCENDING), ("timestamp", ASCENDING)])
    await db["formats"].create_index([("format_id", ASCENDING)], unique=True)


# ---------------------------------------------------------------------------
# Session operations
# ---------------------------------------------------------------------------

async def create_session(session: Session) -> Session:
    db = get_db()
    doc = session.model_dump()
    await db["Orchestrator"].insert_one(doc)
    return session


async def get_session(session_id: str) -> Optional[Session]:
    db = get_db()
    doc = await db["Orchestrator"].find_one({"session_id": session_id}, {"_id": 0})
    if doc is None:
        return None
    return Session.model_validate(doc)


async def update_session(session: Session) -> Session:
    from datetime import datetime
    session.updated_at = datetime.utcnow().isoformat() + "Z"
    db = get_db()
    await db["Orchestrator"].replace_one(
        {"session_id": session.session_id},
        session.model_dump(),
        upsert=True,
    )
    return session


async def delete_session(session_id: str) -> None:
    db = get_db()
    await db["Orchestrator"].delete_one({"session_id": session_id})
    await db["messages"].delete_many({"session_id": session_id})


async def list_sessions(limit: int = 50) -> list[dict]:
    """Returns sessions ordered by creation date (newest first)."""
    db = get_db()
    cursor = db["Orchestrator"].find({}, {"_id": 0}).sort("created_at", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ---------------------------------------------------------------------------
# MOM Document operations
# ---------------------------------------------------------------------------

async def save_mom(mom: MOMDocument) -> MOMDocument:
    db = get_db()
    await db.moms.replace_one(
        {"mom_id": mom.mom_id},
        mom.model_dump(),
        upsert=True,
    )
    return mom


async def get_mom(mom_id: str) -> Optional[MOMDocument]:
    db = get_db()
    doc = await db.moms.find_one({"mom_id": mom_id}, {"_id": 0})
    if doc is None:
        return None
    return MOMDocument.model_validate(doc)


async def get_moms_for_session(session_id: str) -> list[MOMDocument]:
    db = get_db()
    cursor = db.moms.find({"session_id": session_id}, {"_id": 0})
    docs = await cursor.to_list(length=100)
    return [MOMDocument.model_validate(d) for d in docs]


# ---------------------------------------------------------------------------
# Chat message operations
# ---------------------------------------------------------------------------

async def save_message(session_id: str, message: dict) -> None:
    """Persist a single chat message for a session."""
    db = get_db()
    await db.messages.insert_one({"session_id": session_id, **message})


async def get_messages(session_id: str) -> list[dict]:
    """Return all messages for a session, ordered by timestamp."""
    db = get_db()
    cursor = db.messages.find(
        {"session_id": session_id},
        {"_id": 0, "session_id": 0},
    ).sort("timestamp", ASCENDING)
    return await cursor.to_list(length=500)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def ping() -> bool:
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Custom Format operations
# ---------------------------------------------------------------------------

async def save_format(format_data: dict) -> dict:
    """Save a custom format to MongoDB."""
    db = get_db()
    await db.formats.replace_one(
        {"format_id": format_data["id"]},
        format_data,
        upsert=True,
    )
    return format_data


async def get_all_formats() -> list[dict]:
    """Get all custom formats from MongoDB."""
    db = get_db()
    cursor = db.formats.find({}, {"_id": 0})
    return await cursor.to_list(length=100)


async def delete_format(format_id: str) -> None:
    """Delete a custom format from MongoDB."""
    db = get_db()
    await db.formats.delete_one({"format_id": format_id})


# ---------------------------------------------------------------------------
# Audio File Storage (GridFS)
# ---------------------------------------------------------------------------

def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    """Get GridFS bucket for audio file storage."""
    db = get_db()
    return AsyncIOMotorGridFSBucket(db, bucket_name="audio_files")


async def save_audio_file(file_data: bytes, filename: str, content_type: str = "audio/mpeg") -> str:
    """
    Save audio file to MongoDB GridFS.
    Returns the file_id as string.
    """
    bucket = get_gridfs_bucket()
    file_id = await bucket.upload_from_stream(
        filename,
        file_data,
        metadata={"contentType": content_type}
    )
    return str(file_id)


async def get_audio_file(file_id: str) -> Optional[bytes]:
    """
    Retrieve audio file from MongoDB GridFS.
    Returns file bytes or None if not found.
    """
    from bson import ObjectId
    bucket = get_gridfs_bucket()
    try:
        grid_out = await bucket.open_download_stream(ObjectId(file_id))
        return await grid_out.read()
    except Exception:
        return None


async def delete_audio_file(file_id: str) -> None:
    """Delete audio file from MongoDB GridFS."""
    from bson import ObjectId
    bucket = get_gridfs_bucket()
    try:
        await bucket.delete(ObjectId(file_id))
    except Exception:
        pass


"""
MOM Format Registry — AgentMesh AI

Predefined format templates + support for custom uploaded formats.
Each format defines:
  - id, name, description
  - sections: which MOM sections to include and in what order
  - pdf_accent_color: hex color for the PDF header/section titles
  - custom_fields: extra fields specific to the format

Same 9-agent pipeline runs for every format.
Only the formatter output structure and PDF template change.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional
import asyncio

FORMATS_DIR = Path(os.getenv("FORMATS_DIR", "formats/definitions"))
FORMATS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Built-in formats
# ---------------------------------------------------------------------------

BUILTIN_FORMATS: list[dict] = [
    {
        "id": "standard",
        "name": "Standard MOM",
        "description": "Classic Minutes of Meeting with topics, decisions, and action items.",
        "sections": ["topics", "decisions", "actions"],
        "accent_color": "#e6a817",
        "header_color": "#1a1a2e",
        "icon": "📋",
    },
    {
        "id": "agile",
        "name": "Agile / Sprint",
        "description": "Sprint retrospective format: What went well, blockers, action items.",
        "sections": ["topics", "actions"],
        "accent_color": "#38a169",
        "header_color": "#1a365d",
        "icon": "⚡",
        "custom_labels": {
            "topics": "Discussion Points",
            "actions": "Sprint Action Items",
        },
    },
    {
        "id": "client",
        "name": "Client Meeting",
        "description": "Client-facing MOM with requirements, decisions, and follow-ups.",
        "sections": ["topics", "decisions", "actions"],
        "accent_color": "#3182ce",
        "header_color": "#2a4365",
        "icon": "🤝",
        "custom_labels": {
            "topics": "Discussion Summary",
            "decisions": "Agreed Points",
            "actions": "Follow-up Items",
        },
    },
    {
        "id": "project",
        "name": "Project Review",
        "description": "Project status meeting with milestones, risks, and next steps.",
        "sections": ["topics", "decisions", "actions"],
        "accent_color": "#d53f8c",
        "header_color": "#322659",
        "icon": "🗂️",
        "custom_labels": {
            "topics": "Status Updates",
            "decisions": "Milestone Decisions",
            "actions": "Next Steps",
        },
    },
]

# In-memory store for custom uploaded formats
_custom_formats: dict[str, dict] = {}


def get_all_formats() -> list[dict]:
    """Returns all available formats (built-in + custom from MongoDB)."""
    from storage.mongo_client import get_all_formats as get_custom_formats
    
    try:
        # Try to get custom formats from MongoDB
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we can't use asyncio.run
            # Return built-ins only and let the API endpoint handle async
            return BUILTIN_FORMATS
        else:
            customs = loop.run_until_complete(get_custom_formats())
            return BUILTIN_FORMATS + customs
    except:
        # If MongoDB is not available, return built-ins only
        return BUILTIN_FORMATS


async def get_all_formats_async() -> list[dict]:
    """Async version to get all formats including custom ones from MongoDB."""
    from storage.mongo_client import get_all_formats as get_custom_formats
    
    try:
        customs = await get_custom_formats()
        return BUILTIN_FORMATS + customs
    except:
        return BUILTIN_FORMATS


def get_format(format_id: str) -> Optional[dict]:
    """Returns a format by ID, checking built-ins then MongoDB."""
    for f in BUILTIN_FORMATS:
        if f["id"] == format_id:
            return f
    
    # Check in-memory cache first
    if format_id in _custom_formats:
        return _custom_formats[format_id]
    
    # Try to get from MongoDB using pymongo (synchronous)
    try:
        from pymongo import MongoClient
        from storage.mongo_client import MONGO_URL, DB_NAME
        
        # Use synchronous pymongo client for this sync function
        sync_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        db = sync_client[DB_NAME]
        doc = db.formats.find_one({"format_id": format_id}, {"_id": 0})
        sync_client.close()
        
        if doc:
            _custom_formats[format_id] = doc  # Cache it
            return doc
    except Exception as e:
        print(f"[registry] Failed to get format from MongoDB: {e}")
        import traceback
        traceback.print_exc()
    
    return None


def register_custom_format(format_def: dict) -> dict:
    """Registers a user-uploaded custom format and saves to MongoDB."""
    import uuid
    from storage.mongo_client import save_format
    import asyncio
    
    if "id" not in format_def:
        format_def["id"] = f"custom_{uuid.uuid4().hex[:8]}"
    
    format_def["format_id"] = format_def["id"]  # Add format_id for MongoDB
    format_def["is_custom"] = True
    
    # Save to in-memory cache
    _custom_formats[format_def["id"]] = format_def
    
    # Save to MongoDB asynchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a task if loop is already running
            asyncio.create_task(save_format(format_def))
        else:
            loop.run_until_complete(save_format(format_def))
        print(f"[registry] Saved custom format '{format_def['id']}' to MongoDB")
    except Exception as e:
        print(f"[registry] Failed to save format to MongoDB: {e}")
        import traceback
        traceback.print_exc()
    
    return format_def


def get_default_format() -> dict:
    return BUILTIN_FORMATS[0]

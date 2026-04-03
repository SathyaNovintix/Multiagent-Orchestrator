"""
Universal Message Contract — AgentMesh AI
All components (UI, Orchestrator, Agents) use these schemas exclusively.
This contract must never be broken.
"""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ---------------------------------------------------------------------------
# Input / Request Schema (UI → Orchestrator → Agent)
# ---------------------------------------------------------------------------

class Payload(BaseModel):
    input_type: Literal["text", "audio"]
    content: str                        # Raw text or audio file URL
    language: Optional[str] = None      # Optional language hint


class Context(BaseModel):
    conversation_history: list[dict] = Field(default_factory=list)
    intermediate_data: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)


class Meta(BaseModel):
    source: str                         # "user" | "orchestrator" | agent_name
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class AgentRequest(BaseModel):
    session_id: str
    intent: str                         # "generate_mom" | "auto_detect" | etc.
    payload: Payload
    context: Context = Field(default_factory=Context)
    meta: Meta


# ---------------------------------------------------------------------------
# Agent Response Schema (Agent → Orchestrator)
# ---------------------------------------------------------------------------

class ResponseData(BaseModel):
    output: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ResponseMeta(BaseModel):
    agent: str
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    execution_ms: Optional[int] = None


class AgentResponse(BaseModel):
    session_id: str
    status: Literal["success", "fail", "need_more_input", "route"]
    intent: Optional[str] = None        # Agent can refine intent
    data: ResponseData = Field(default_factory=ResponseData)
    next_agents: list[str] = Field(default_factory=list)   # Suggestions only
    reasoning: str = ""
    meta: ResponseMeta


# ---------------------------------------------------------------------------
# Session Model (stored in Redis)
# ---------------------------------------------------------------------------

class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str = "New Session"
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    intent: str = "auto_detect"
    status: Literal["active", "completed", "error"] = "active"
    conversation_history: list[dict] = Field(default_factory=list)
    intermediate_data: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# MOM Document Model (stored in Redis after generation)
# ---------------------------------------------------------------------------

class Topic(BaseModel):
    title: str
    summary: str
    timestamp: Optional[str] = None


class Decision(BaseModel):
    decision: str
    owner: str
    condition: Optional[str] = None


class Action(BaseModel):
    task: str
    owner: str
    deadline: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "medium"


class MOMDocument(BaseModel):
    mom_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    participants: list[str] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    source_language: str = "en"
    original_language: str = "en"
    file_url: Optional[str] = None      # PDF download URL
    format_id: str = "standard"         # The template ID used (standard, agile, custom_...)
    # Custom template data (populated when a custom uploaded template is used)
    sections: Optional[dict[str, Any]] = None
    template_structure: Optional[dict[str, Any]] = None

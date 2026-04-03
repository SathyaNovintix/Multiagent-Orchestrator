"""
LangGraph State — AgentMesh AI

The single shared state object that flows through every node in the graph.
Replaces the per-agent Context + intermediate_data pattern for in-graph execution.
Redis still persists the final session; this state lives only during graph execution.
"""
from __future__ import annotations
from typing import Any, Literal, Optional
from typing_extensions import TypedDict


class AgentMeshState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────────────
    session_id: str
    intent: str                         # "generate_mom" | "general_summary" | "auto_detect"

    # ── Raw Input ─────────────────────────────────────────────────────────
    input_type: Literal["text", "audio"]
    content: str                        # Raw text or audio file URL
    language_hint: Optional[str]        # Optional user-provided language

    # ── After speech_to_text ──────────────────────────────────────────────
    transcript: Optional[str]

    # ── After language_detector ───────────────────────────────────────────
    detected_language: Optional[str]    # ISO lang code e.g. "ta", "en"
    language_confidence: float

    # ── After translator ──────────────────────────────────────────────────
    english_transcript: Optional[str]

    # ── After intent_refiner ──────────────────────────────────────────────
    refined_intent: Optional[str]
    intent_confidence: float

    # ── After parallel extraction ─────────────────────────────────────────
    topics: list[dict]
    decisions: list[dict]
    actions: list[dict]

    # ── After formatter ───────────────────────────────────────────────────
    structured_mom: Optional[dict]

    # ── After response_generator ──────────────────────────────────────────
    user_message: Optional[str]
    file_url: Optional[str]
    format_id: str

    # ── Pipeline control ──────────────────────────────────────────────────
    status: Literal["running", "completed", "error", "needs_clarification"]
    error_message: Optional[str]
    clarification_prompt: Optional[str]

    # ── Conversation history (passed in, not modified by graph) ───────────
    conversation_history: list[dict]
    memory: dict[str, Any]

    # ── Execution trace (agent execution details) ─────────────────────────
    trace: list[dict]

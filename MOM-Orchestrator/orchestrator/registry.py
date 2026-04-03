"""
Agent Registry — AgentMesh AI

Static lookup of all 9 agents.
Adding a new use case = register new agent instances here.
The LangGraph nodes in core.py look up agents by name from this registry.

Intent → Capability → Agent routing tables are also defined here.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent

# ---------------------------------------------------------------------------
# Level 1: Intent → Capabilities
# ---------------------------------------------------------------------------
INTENT_CAPABILITIES: dict[str, list[str]] = {
    "generate_mom": [
        "input_processing",
        "language_processing",
        "context_building",
        "extraction",
        "formatting",
        "response",
    ],
    "general_summary": [
        "input_processing",
        "language_processing",
        "context_building",
        "formatting",
        "response",
    ],
    "auto_detect": [
        "input_processing",
        "language_processing",
        "context_building",
        "extraction",
        "formatting",
        "response",
    ],
}

# ---------------------------------------------------------------------------
# Level 2: Capability → Agent names
# The LangGraph graph uses these for documentation/reference.
# Actual routing is done via conditional edges in core.py.
# ---------------------------------------------------------------------------
CAPABILITY_TO_AGENTS: dict[str, list[str]] = {
    "input_processing":    ["speech_to_text"],
    "language_processing": ["language_detector", "translator"],
    "context_building":    ["intent_refiner"],
    "extraction":          ["topic_extractor", "decision_extractor", "action_extractor"],  # parallel
    "formatting":          ["formatter"],
    "response":            ["response_generator"],
}

# Agents in this set run concurrently (asyncio.gather in the extraction node)
PARALLEL_AGENTS: set[str] = {"topic_extractor", "decision_extractor", "action_extractor"}

# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------
AGENT_REGISTRY: dict[str, "BaseAgent"] = {}


def build_registry() -> None:
    """
    Instantiates all agents and populates AGENT_REGISTRY.
    Called once at app startup before init_orchestrator().
    """
    from agents.speech_to_text import SpeechToTextAgent
    from agents.language_detector import LanguageDetectorAgent
    from agents.translator import TranslatorAgent
    from agents.intent_refiner import IntentRefinerAgent
    from agents.topic_extractor import TopicExtractorAgent
    from agents.decision_extractor import DecisionExtractorAgent
    from agents.action_extractor import ActionExtractorAgent
    from agents.formatter import FormatterAgent
    from agents.response_generator import ResponseGeneratorAgent
    from agents.conversational import ConversationalAgent

    agents: list[BaseAgent] = [
        SpeechToTextAgent(),
        LanguageDetectorAgent(),
        TranslatorAgent(),
        IntentRefinerAgent(),
        TopicExtractorAgent(),
        DecisionExtractorAgent(),
        ActionExtractorAgent(),
        FormatterAgent(),
        ResponseGeneratorAgent(),
        ConversationalAgent(),
    ]

    for agent in agents:
        AGENT_REGISTRY[agent.name] = agent

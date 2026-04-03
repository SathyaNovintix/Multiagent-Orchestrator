"""
Intent Refiner Agent Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class IntentReasoningResult(BaseModel):
    """Result from intent reasoning"""
    thought: str
    detected_intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    requires_full_processing: bool
    suggested_next_agents: List[str] = []


class IntentContext(BaseModel):
    """Context for intent analysis"""
    input_type: str
    input_length: int
    language_hint: Optional[str] = None
    current_intent: str = "auto_detect"

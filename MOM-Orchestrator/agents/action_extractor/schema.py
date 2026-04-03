"""Action Extractor Agent Schemas"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ActionReasoningResult(BaseModel):
    """Result from action extraction reasoning"""
    thought: str
    num_actions_estimated: int
    extraction_strategy: str
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]


class Action(BaseModel):
    """Extracted action item structure"""
    task: str
    owner: str
    deadline: str = "Not specified"
    priority: str = "medium"
    ambiguous: bool = False

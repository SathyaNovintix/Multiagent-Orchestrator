"""Decision Extractor Agent Schemas"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DecisionReasoningResult(BaseModel):
    """Result from decision extraction reasoning"""
    thought: str
    num_decisions_estimated: int
    extraction_approach: str
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]


class Decision(BaseModel):
    """Extracted decision structure"""
    decision: str
    owner: str
    context: Optional[str] = None
    impact: Optional[str] = None

"""Response Generator Agent Schemas"""
from typing import List
from pydantic import BaseModel, Field


class ResponseReasoningResult(BaseModel):
    """Result from response generation reasoning"""
    thought: str
    response_strategy: str
    highlight_items: List[str]
    tone: str
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]

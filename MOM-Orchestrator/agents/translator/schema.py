"""Translator Agent Schemas"""
from typing import List
from pydantic import BaseModel, Field


class TranslatorReasoningResult(BaseModel):
    """Result from translation reasoning"""
    thought: str
    translation_strategy: str
    complexity: str
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]

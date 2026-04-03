"""Language Detector Agent Schemas"""
from typing import List, Optional
from pydantic import BaseModel, Field


class LanguageReasoningResult(BaseModel):
    """Result from language detection reasoning"""
    thought: str
    detected_language: str
    language_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    mixed_languages: bool = False
    secondary_languages: List[str] = []
    plan: List[str]

"""Speech to Text Agent Schemas"""
from typing import List
from pydantic import BaseModel, Field


class SpeechReasoningResult(BaseModel):
    """Result from speech-to-text reasoning"""
    thought: str
    transcription_strategy: str
    expected_quality: str
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]

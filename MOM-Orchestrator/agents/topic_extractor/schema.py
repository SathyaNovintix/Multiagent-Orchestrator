"""Topic Extractor Agent Schemas"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TopicReasoningResult(BaseModel):
    """Result from topic extraction reasoning"""
    thought: str
    num_topics_estimated: int
    extraction_strategy: str
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]


class Topic(BaseModel):
    """Extracted topic structure"""
    title: str
    summary: str
    participants: List[str] = []
    duration: Optional[str] = None


class TopicExtractionResult(BaseModel):
    """Result from topic extraction"""
    topics: List[Topic]
    extraction_method: str
    confidence: float

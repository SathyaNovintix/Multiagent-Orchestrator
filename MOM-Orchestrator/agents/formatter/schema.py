"""Formatter Agent Schemas"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FormatterReasoningResult(BaseModel):
    """Result from formatting reasoning"""
    thought: str
    formatting_strategy: str
    section_order: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    plan: List[str]


class FormattedSection(BaseModel):
    """Formatted MOM section"""
    label: str
    items: List[Dict[str, Any]]


class FormattedMOM(BaseModel):
    """Complete formatted MOM"""
    title: str
    metadata: Dict[str, Any]
    sections: Dict[str, FormattedSection]

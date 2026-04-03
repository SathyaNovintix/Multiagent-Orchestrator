"""
Conversational Agent Schemas
Defines data structures and contracts for the conversational agent.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ReasoningResult(BaseModel):
    """Result from the reasoning step of ReAct pattern"""
    thought: str = Field(description="Agent's analysis of the situation")
    user_intent: str = Field(description="Detected user intent")
    requires_meeting_data: bool = Field(description="Whether meeting data is required")
    can_answer_without_data: bool = Field(description="Whether can answer without meeting data")
    plan: List[str] = Field(description="Steps the agent plans to take")
    action_type: str = Field(description="Type of action to perform")
    confidence: float = Field(description="Confidence in the reasoning", ge=0.0, le=1.0)


class ActionResult(BaseModel):
    """Result from the acting step of ReAct pattern"""
    user_message: str = Field(description="Generated response message")
    reasoning: str = Field(description="Reasoning behind the response")
    action_taken: str = Field(description="Type of action that was taken")


class ObservationResult(BaseModel):
    """Result from the observation step of ReAct pattern"""
    observation: str = Field(description="What was observed from the action")
    is_complete: bool = Field(description="Whether the task is complete")
    next_step: Optional[str] = Field(description="Next step if not complete", default=None)


class ConversationalContext(BaseModel):
    """Context available to the conversational agent"""
    has_transcript: bool = False
    has_topics: bool = False
    has_decisions: bool = False
    has_actions: bool = False
    transcript_length: int = 0
    num_topics: int = 0
    num_decisions: int = 0
    num_actions: int = 0
    conversation_history: List[Dict[str, Any]] = []
    
    @classmethod
    def from_request_data(cls, data: Dict[str, Any], history: Optional[List[Dict[str, Any]]]) -> "ConversationalContext":
        """Create context from request data"""
        # Handle None values safely
        safe_data = data or {}
        safe_history = history or []
        
        return cls(
            has_transcript=bool(safe_data.get("transcript")),
            has_topics=bool(safe_data.get("topics")),
            has_decisions=bool(safe_data.get("decisions")),
            has_actions=bool(safe_data.get("actions")),
            transcript_length=len(safe_data.get("transcript") or ""),
            num_topics=len(safe_data.get("topics") or []),
            num_decisions=len(safe_data.get("decisions") or []),
            num_actions=len(safe_data.get("actions") or []),
            conversation_history=safe_history[-3:] if safe_history else [],
        )

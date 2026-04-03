"""
Base Agent — AgentMesh AI
All agents inherit from this class.
Agents are STATELESS — they receive full context every call and maintain no internal state.
Supports ReAct pattern (Reasoning + Acting) for intelligent decision-making.
"""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from schemas.contracts import AgentRequest, AgentResponse, ResponseData, ResponseMeta


class BaseAgent(ABC):
    """
    Abstract base for all AgentMesh agents.
    
    Supports ReAct Pattern:
    - Reasoning: Agent thinks about what to do
    - Acting: Agent performs actions based on reasoning
    - Observation: Agent observes results and decides next steps

    Rules:
    - Never store state between calls.
    - Always return a valid AgentResponse.
    - next_agents is a suggestion — the orchestrator decides what runs.
    - Include human-readable reasoning in every response.
    - Agents are reusable across different purposes via configuration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique agent identifier (must match AGENT_REGISTRY key)."""
        ...

    @abstractmethod
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Core logic — implemented by each agent."""
        ...
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct Step 1: Reasoning
        Agent analyzes the request and context to decide what actions to take.
        Override this in subclasses for custom reasoning logic.
        
        Returns:
            Dict with reasoning results: {
                'thought': str,  # What the agent is thinking
                'plan': List[str],  # Steps the agent plans to take
                'should_act': bool,  # Whether action is needed
                'action_type': str,  # Type of action to perform
            }
        """
        return {
            'thought': 'Processing request',
            'plan': ['Execute default logic'],
            'should_act': True,
            'action_type': 'default',
        }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct Step 2: Acting
        Agent performs actions based on reasoning results.
        Override this in subclasses for custom action logic.
        
        Returns:
            Dict with action results
        """
        return {}
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct Step 3: Observation
        Agent observes the results of actions and decides if more steps are needed.
        Override this in subclasses for custom observation logic.
        
        Returns:
            Dict with observation results: {
                'observation': str,  # What the agent observed
                'is_complete': bool,  # Whether the task is complete
                'next_step': Optional[str],  # Next step if not complete
            }
        """
        return {
            'observation': 'Action completed',
            'is_complete': True,
            'next_step': None,
        }

    async def run(self, request: AgentRequest) -> AgentResponse:
        """
        Wraps _execute with timing and error handling.
        The orchestrator always calls this method, never _execute directly.
        """
        start = time.monotonic()
        try:
            response = await self._execute(request)
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            response = AgentResponse(
                session_id=request.session_id,
                status="fail",
                reasoning=f"{self.name} raised an unhandled exception: {exc}",
                meta=ResponseMeta(agent=self.name, execution_ms=elapsed_ms),
            )
        else:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            response.meta.execution_ms = elapsed_ms

        return response

    # ------------------------------------------------------------------
    # Helpers for building responses
    # ------------------------------------------------------------------

    def success(
        self,
        session_id: str,
        output: dict,
        confidence: float = 1.0,
        next_agents: list[str] | None = None,
        reasoning: str = "",
        refined_intent: str | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            session_id=session_id,
            status="success",
            intent=refined_intent,
            data=ResponseData(output=output, confidence=confidence),
            next_agents=next_agents or [],
            reasoning=reasoning,
            meta=ResponseMeta(agent=self.name),
        )

    def fail(self, session_id: str, reasoning: str) -> AgentResponse:
        return AgentResponse(
            session_id=session_id,
            status="fail",
            reasoning=reasoning,
            meta=ResponseMeta(agent=self.name),
        )

    def need_more_input(
        self,
        session_id: str,
        clarification_prompt: str,
    ) -> AgentResponse:
        return AgentResponse(
            session_id=session_id,
            status="need_more_input",
            data=ResponseData(
                output={"clarification_prompt": clarification_prompt}
            ),
            reasoning=f"{self.name} requires clarification from user.",
            meta=ResponseMeta(agent=self.name),
        )

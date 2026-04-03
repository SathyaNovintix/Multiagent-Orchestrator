"""Decision Extractor Agent - AI-Driven with ReAct Pattern"""
from __future__ import annotations
from typing import Dict, Any
from llm.bedrock_client import invoke_llm_json
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent
from .prompts import (
    REASONING_SYSTEM_PROMPT,
    REASONING_USER_TEMPLATE,
    ACTING_SYSTEM_PROMPT,
    ACTING_USER_TEMPLATE,
)


class DecisionExtractorAgent(BaseAgent):
    name = "decision_extractor"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes transcript to plan decision extraction"""
        data = request.context.intermediate_data
        text = data.get("english_transcript") or data.get("transcript") or request.payload.content
        
        if not text:
            return {'thought': 'No transcript available', 'should_act': False}
        
        user_prompt = REASONING_USER_TEMPLATE.format(transcript=text[:2000])
        
        try:
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            return {
                'thought': result.get('thought', 'Analyzing decisions'),
                'num_decisions_estimated': result.get('num_decisions_estimated', 2),
                'extraction_approach': result.get('extraction_approach', 'both'),
                'confidence': result.get('confidence', 0.85),
                'plan': result.get('plan', ['Extract decisions']),
                'should_act': True,
            }
        except Exception as exc:
            return {
                'thought': f'AI reasoning failed: {exc}',
                'num_decisions_estimated': 2,
                'extraction_approach': 'both',
                'confidence': 0.7,
                'plan': ['Extract decisions with fallback'],
                'should_act': True,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """AI extracts decisions based on reasoning"""
        data = request.context.intermediate_data
        text = data.get("english_transcript") or data.get("transcript") or request.payload.content
        
        user_prompt = ACTING_USER_TEMPLATE.format(
            transcript=text[:4000],
            extraction_approach=reasoning['extraction_approach'],
            num_decisions_estimated=reasoning['num_decisions_estimated'],
        )
        
        try:
            decisions = await invoke_llm_json(ACTING_SYSTEM_PROMPT, user_prompt)
            if isinstance(decisions, list):
                return {'decisions': decisions, 'extraction_method': reasoning['extraction_approach']}
            elif isinstance(decisions, dict) and 'decisions' in decisions:
                return {'decisions': decisions['decisions'], 'extraction_method': reasoning['extraction_approach']}
            else:
                return {'decisions': [], 'extraction_method': 'failed'}
        except Exception as exc:
            return {'decisions': [], 'extraction_method': f'error: {exc}'}
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify decision extraction quality"""
        decisions = action_result.get('decisions', [])
        return {
            'observation': f"Extracted {len(decisions)} decisions using {action_result.get('extraction_method')}",
            'is_complete': True,  # Can be 0 decisions
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for decision extraction"""
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        if not reasoning['should_act']:
            return self.fail(session_id=request.session_id, reasoning="No transcript available")
        
        action_result = await self._act(request, reasoning)
        observation = await self._observe(request, action_result)
        
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Plan] {', '.join(reasoning['plan'])}\n"
            f"[Action] {action_result.get('extraction_method')}\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={"decisions": action_result['decisions']},
            confidence=reasoning['confidence'],
            reasoning=full_reasoning,
        )

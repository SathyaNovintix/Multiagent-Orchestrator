"""Action Extractor Agent - AI-Driven with ReAct Pattern"""
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


class ActionExtractorAgent(BaseAgent):
    name = "action_extractor"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes transcript to plan action extraction"""
        data = request.context.intermediate_data
        text = data.get("english_transcript") or data.get("transcript") or request.payload.content
        
        if not text:
            return {'thought': 'No transcript available', 'should_act': False}
        
        user_prompt = REASONING_USER_TEMPLATE.format(transcript=text[:2000])
        
        try:
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            return {
                'thought': result.get('thought', 'Analyzing action items'),
                'num_actions_estimated': result.get('num_actions_estimated', 3),
                'extraction_strategy': result.get('extraction_strategy', 'both'),
                'confidence': result.get('confidence', 0.85),
                'plan': result.get('plan', ['Extract actions']),
                'should_act': True,
            }
        except Exception as exc:
            return {
                'thought': f'AI reasoning failed: {exc}',
                'num_actions_estimated': 3,
                'extraction_strategy': 'both',
                'confidence': 0.7,
                'plan': ['Extract actions with fallback'],
                'should_act': True,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """AI extracts actions based on reasoning"""
        data = request.context.intermediate_data
        text = data.get("english_transcript") or data.get("transcript") or request.payload.content
        
        user_prompt = ACTING_USER_TEMPLATE.format(
            transcript=text[:4000],
            extraction_strategy=reasoning['extraction_strategy'],
            num_actions_estimated=reasoning['num_actions_estimated'],
        )
        
        try:
            actions = await invoke_llm_json(ACTING_SYSTEM_PROMPT, user_prompt)
            if isinstance(actions, list):
                return {'actions': actions, 'extraction_method': reasoning['extraction_strategy']}
            elif isinstance(actions, dict) and 'actions' in actions:
                return {'actions': actions['actions'], 'extraction_method': reasoning['extraction_strategy']}
            else:
                return {'actions': [], 'extraction_method': 'failed'}
        except Exception as exc:
            return {'actions': [], 'extraction_method': f'error: {exc}'}
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify action extraction quality"""
        actions = action_result.get('actions', [])
        ambiguous = [a for a in actions if a.get('ambiguous', False)]
        return {
            'observation': f"Extracted {len(actions)} actions ({len(ambiguous)} ambiguous) using {action_result.get('extraction_method')}",
            'is_complete': True,
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for action extraction"""
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
            output={"actions": action_result['actions']},
            confidence=reasoning['confidence'],
            reasoning=full_reasoning,
        )

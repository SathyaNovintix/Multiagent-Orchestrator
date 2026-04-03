"""
IntentRefinerAgent — AI-Driven Intent Detection with ReAct Pattern
Fully dynamic, no hardcoded patterns.
"""
from __future__ import annotations
from typing import Dict, Any
from llm.bedrock_client import invoke_llm_json
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent
from .schema import IntentContext, IntentReasoningResult
from .prompts import (
    REASONING_SYSTEM_PROMPT,
    REASONING_USER_TEMPLATE,
)


class IntentRefinerAgent(BaseAgent):
    """AI-driven intent detection using ReAct pattern"""
    name = "intent_refiner"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes input to determine intent"""
        data = request.context.intermediate_data
        text = (
            data.get("english_transcript")
            or data.get("transcript")
            or request.payload.content
        )
        
        if not text:
            return {
                'thought': 'No text available for analysis',
                'detected_intent': request.intent,
                'confidence': 0.0,
                'should_act': False,
            }
        
        # Build context
        intent_context = IntentContext(
            input_type=request.payload.input_type,
            input_length=len(text),
            language_hint=request.payload.language,
            current_intent=request.intent,
        )
        
        # AI reasoning prompt
        user_prompt = REASONING_USER_TEMPLATE.format(
            user_input=text[:500],  # First 500 chars for analysis
            input_type=intent_context.input_type,
            input_length=intent_context.input_length,
            language_hint=intent_context.language_hint or "not specified",
            current_intent=intent_context.current_intent,
        )
        
        try:
            # AI determines intent
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            
            return {
                'thought': result.get('thought', 'Analyzing intent'),
                'detected_intent': result.get('detected_intent', request.intent),
                'confidence': float(result.get('confidence', 0.85)),
                'reasoning': result.get('reasoning', ''),
                'requires_full_processing': result.get('requires_full_processing', True),
                'suggested_next_agents': result.get('suggested_next_agents', []),
                'should_act': True,
            }
        except Exception as exc:
            # Fallback: keep original intent
            return {
                'thought': f'AI intent detection failed ({exc}), keeping original intent',
                'detected_intent': request.intent,
                'confidence': 0.75,
                'reasoning': 'Fallback to original intent',
                'requires_full_processing': True,
                'suggested_next_agents': [],
                'should_act': True,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Confirm and finalize intent"""
        return {
            'refined_intent': reasoning['detected_intent'],
            'intent_confidence': reasoning['confidence'],
            'reasoning': reasoning['reasoning'],
        }
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify intent refinement is complete"""
        return {
            'observation': f"Intent refined to '{action_result['refined_intent']}' with confidence {action_result['intent_confidence']:.2f}",
            'is_complete': True,
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for intent refinement"""
        # Reasoning
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        if not reasoning['should_act']:
            return self.fail(
                session_id=request.session_id,
                reasoning="No text available for intent refinement.",
            )
        
        # Acting
        action_result = await self._act(request, reasoning)
        
        # Observation
        observation = await self._observe(request, action_result)
        
        # Build response
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Analysis] {reasoning['reasoning']}\n"
            f"[Action] Refined intent to '{action_result['refined_intent']}'\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={"intent_confidence": action_result['intent_confidence']},
            confidence=action_result['intent_confidence'],
            refined_intent=action_result['refined_intent'],
            reasoning=full_reasoning,
        )

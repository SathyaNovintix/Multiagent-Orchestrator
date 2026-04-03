"""Translator Agent - AI-Driven with ReAct Pattern"""
from __future__ import annotations
from typing import Dict, Any
from llm.bedrock_client import invoke_llm, invoke_llm_json
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent
from .prompts import (
    REASONING_SYSTEM_PROMPT,
    REASONING_USER_TEMPLATE,
    ACTING_SYSTEM_PROMPT,
    ACTING_USER_TEMPLATE,
)


class TranslatorAgent(BaseAgent):
    name = "translator"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes text and plans translation"""
        data = request.context.intermediate_data
        text = data.get("transcript") or request.payload.content
        source_lang = data.get("detected_language", "unknown")
        
        if not text or source_lang in ("en", "english"):
            return {'thought': 'No translation needed', 'should_act': False}
        
        user_prompt = REASONING_USER_TEMPLATE.format(
            source_text=text[:1000],
            source_language=source_lang,
        )
        
        try:
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            return {
                'thought': result.get('thought', 'Planning translation'),
                'translation_strategy': result.get('translation_strategy', 'contextual'),
                'complexity': result.get('complexity', 'moderate'),
                'confidence': result.get('confidence', 0.85),
                'plan': result.get('plan', ['Translate to English']),
                'should_act': True,
                'source_language': source_lang,
            }
        except Exception as exc:
            return {
                'thought': f'AI reasoning failed: {exc}',
                'translation_strategy': 'direct',
                'complexity': 'moderate',
                'confidence': 0.7,
                'plan': ['Translate with fallback'],
                'should_act': True,
                'source_language': source_lang,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """AI translates based on reasoning"""
        data = request.context.intermediate_data
        text = data.get("transcript") or request.payload.content
        
        system_prompt = ACTING_SYSTEM_PROMPT.format(source_language=reasoning['source_language'])
        user_prompt = ACTING_USER_TEMPLATE.format(
            source_language=reasoning['source_language'],
            source_text=text,
            translation_strategy=reasoning['translation_strategy'],
            complexity=reasoning['complexity'],
        )
        
        try:
            translated = await invoke_llm(system_prompt, user_prompt)
            return {
                'english_transcript': translated,
                'translation_method': reasoning['translation_strategy'],
            }
        except Exception as exc:
            return {
                'english_transcript': text,  # Fallback to original
                'translation_method': f'error: {exc}',
            }
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify translation quality"""
        translated = action_result.get('english_transcript', '')
        return {
            'observation': f"Translated {len(translated)} characters using {action_result.get('translation_method')}",
            'is_complete': len(translated) > 0,
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for translation"""
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        if not reasoning['should_act']:
            # No translation needed
            data = request.context.intermediate_data
            return self.success(
                session_id=request.session_id,
                output={"english_transcript": data.get("transcript") or request.payload.content},
                confidence=1.0,
                reasoning="No translation needed - already English",
            )
        
        action_result = await self._act(request, reasoning)
        observation = await self._observe(request, action_result)
        
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Plan] {', '.join(reasoning['plan'])}\n"
            f"[Action] {action_result.get('translation_method')}\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={"english_transcript": action_result['english_transcript']},
            confidence=reasoning['confidence'],
            reasoning=full_reasoning,
        )

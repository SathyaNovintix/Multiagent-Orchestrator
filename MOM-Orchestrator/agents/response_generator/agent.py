"""Response Generator Agent - AI-Driven with ReAct Pattern"""
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


class ResponseGeneratorAgent(BaseAgent):
    name = "response_generator"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes MOM data and plans response"""
        data = request.context.intermediate_data
        mom = data.get("structured_mom") or {}
        
        topics = mom.get("topics") or []
        decisions = mom.get("decisions") or []
        actions = mom.get("actions") or []
        ambiguous = [a for a in actions if a.get("ambiguous")]
        
        user_prompt = REASONING_USER_TEMPLATE.format(
            num_topics=len(topics),
            num_decisions=len(decisions),
            num_actions=len(actions),
            num_ambiguous=len(ambiguous),
            original_language=mom.get("original_language", "en"),
            has_file_url="yes" if data.get("file_url") else "no",
        )
        
        try:
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            return {
                'thought': result.get('thought', 'Planning response'),
                'response_strategy': result.get('response_strategy', 'summary'),
                'highlight_items': result.get('highlight_items', ['topics', 'decisions', 'actions']),
                'tone': result.get('tone', 'professional'),
                'confidence': result.get('confidence', 0.9),
                'plan': result.get('plan', ['Generate response']),
                'should_act': True,
            }
        except Exception as exc:
            return {
                'thought': f'AI reasoning failed: {exc}',
                'response_strategy': 'summary',
                'highlight_items': ['topics', 'decisions', 'actions'],
                'tone': 'professional',
                'confidence': 0.8,
                'plan': ['Generate with fallback'],
                'should_act': True,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """AI generates user response"""
        data = request.context.intermediate_data
        mom = data.get("structured_mom") or {}
        file_url = data.get("file_url") or mom.get("file_url")
        
        topics = mom.get("topics") or []
        decisions = mom.get("decisions") or []
        actions = mom.get("actions") or []
        ambiguous = [a for a in actions if a.get("ambiguous")]
        
        # Prepare previews
        topics_preview = "\n".join([f"- {t.get('title', 'Untitled')}" for t in topics[:5]])
        decisions_preview = "\n".join([f"- {d.get('decision', '')[:80]}" for d in decisions[:3]])
        actions_preview = "\n".join([f"- {a.get('task', '')[:80]}" for a in actions[:5]])
        
        warnings = []
        if ambiguous:
            warnings.append(f"{len(ambiguous)} action(s) have ambiguous ownership")
        
        user_prompt = ACTING_USER_TEMPLATE.format(
            num_topics=len(topics),
            topics_preview=topics_preview or "None",
            num_decisions=len(decisions),
            decisions_preview=decisions_preview or "None",
            num_actions=len(actions),
            actions_preview=actions_preview or "None",
            warnings=", ".join(warnings) if warnings else "None",
            file_url=file_url or "Not available",
            original_language=mom.get("original_language", "en"),
            response_strategy=reasoning['response_strategy'],
            tone=reasoning['tone'],
        )
        
        try:
            message = await invoke_llm(ACTING_SYSTEM_PROMPT, user_prompt)
            return {
                'user_message': message,
                'file_url': file_url,
                'generation_method': reasoning['response_strategy'],
            }
        except Exception as exc:
            # Fallback message
            return {
                'user_message': f"Your MOM has been generated with {len(topics)} topics, {len(decisions)} decisions, and {len(actions)} actions.",
                'file_url': file_url,
                'generation_method': f'fallback: {exc}',
            }
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify response quality"""
        message = action_result.get('user_message', '')
        return {
            'observation': f"Generated response with {len(message)} characters using {action_result.get('generation_method')}",
            'is_complete': len(message) > 0,
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for response generation"""
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        if not reasoning['should_act']:
            return self.fail(session_id=request.session_id, reasoning="No MOM data available")
        
        action_result = await self._act(request, reasoning)
        observation = await self._observe(request, action_result)
        
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Plan] {', '.join(reasoning['plan'])}\n"
            f"[Action] {action_result.get('generation_method')}\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={
                "user_message": action_result['user_message'],
                "file_url": action_result['file_url'],
            },
            confidence=reasoning['confidence'],
            reasoning=full_reasoning,
        )

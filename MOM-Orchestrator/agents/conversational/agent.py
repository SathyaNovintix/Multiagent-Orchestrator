"""
ConversationalAgent — Chat Agent with ReAct Pattern
Modular, reusable agent following ReAct (Reasoning + Acting) pattern.
"""
from __future__ import annotations
from typing import Dict, Any
from llm.bedrock_client import invoke_llm, invoke_llm_json
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent
from .schema import ConversationalContext, ReasoningResult, ActionResult, ObservationResult
from .prompts import (
    REASONING_SYSTEM_PROMPT,
    REASONING_USER_TEMPLATE,
    ACTING_SYSTEM_PROMPT,
    ACTING_USER_TEMPLATE_WITH_DATA,
    ACTING_USER_TEMPLATE_NO_DATA,
)


class ConversationalAgent(BaseAgent):
    """
    Conversational agent using ReAct pattern.
    Reusable for any conversational task by changing prompts and context.
    """
    name = "conversational_agent"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct Step 1: Reasoning
        AI analyzes the situation and decides the strategy (no hardcoded logic).
        """
        data = request.context.intermediate_data
        
        # Build structured context
        conv_context = ConversationalContext.from_request_data(
            data, 
            request.context.conversation_history
        )
        
        # Format conversation history
        history_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')[:100]}" 
            for msg in (conv_context.conversation_history or [])
        ]) if conv_context.conversation_history else 'No previous conversation'
        
        # Build reasoning prompt
        user_prompt = REASONING_USER_TEMPLATE.format(
            user_input=request.payload.content,
            has_transcript=conv_context.has_transcript,
            transcript_length=conv_context.transcript_length,
            has_topics=conv_context.has_topics,
            num_topics=conv_context.num_topics,
            has_decisions=conv_context.has_decisions,
            num_decisions=conv_context.num_decisions,
            has_actions=conv_context.has_actions,
            num_actions=conv_context.num_actions,
            conversation_history=history_text,
        )
        
        try:
            # AI does the reasoning
            reasoning_result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            
            return {
                'thought': reasoning_result.get('thought', 'Analyzing user input'),
                'plan': reasoning_result.get('plan', ['Respond to user']),
                'should_act': True,
                'action_type': reasoning_result.get('action_type', 'general_response'),
                'user_intent': reasoning_result.get('user_intent', 'other'),
                'requires_meeting_data': reasoning_result.get('requires_meeting_data', False),
                'can_answer_without_data': reasoning_result.get('can_answer_without_data', True),
                'confidence': reasoning_result.get('confidence', 0.8),
                'has_meeting_data': any([
                    conv_context.has_transcript, 
                    conv_context.has_topics,
                    conv_context.has_decisions, 
                    conv_context.has_actions
                ]),
            }
        except Exception as exc:
            # Fallback reasoning if AI reasoning fails
            return {
                'thought': f'AI reasoning failed ({exc}), using fallback',
                'plan': ['Respond conversationally'],
                'should_act': True,
                'action_type': 'general_response',
                'user_intent': 'other',
                'requires_meeting_data': False,
                'can_answer_without_data': True,
                'confidence': 0.5,
                'has_meeting_data': False,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct Step 2: Acting
        AI generates response based on reasoning results.
        """
        data = request.context.intermediate_data
        
        # Build meeting context
        context_parts = []
        if data.get("transcript"):
            context_parts.append(f"Meeting Transcript:\n{data['transcript'][:3000]}")
        if data.get("topics"):
            topics_text = "\n".join([f"- {t.get('title', '')}: {t.get('summary', '')}" for t in data["topics"][:5]])
            context_parts.append(f"\nDiscussion Topics:\n{topics_text}")
        if data.get("decisions"):
            decisions_text = "\n".join([f"- {d.get('decision', '')} (Owner: {d.get('owner', 'N/A')})" for d in data["decisions"][:5]])
            context_parts.append(f"\nDecisions Made:\n{decisions_text}")
        if data.get("actions"):
            actions_text = "\n".join([f"- {a.get('task', '')} (Owner: {a.get('owner', 'TBD')}, Deadline: {a.get('deadline', 'N/A')})" for a in data["actions"][:5]])
            context_parts.append(f"\nAction Items:\n{actions_text}")
        
        # Build conversation history
        history = (request.context.conversation_history or [])[-5:] if request.context.conversation_history else []
        history_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history])
        
        # Choose prompt template based on data availability
        if reasoning['has_meeting_data']:
            user_prompt = ACTING_USER_TEMPLATE_WITH_DATA.format(
                meeting_context=chr(10).join(context_parts),
                conversation_history=history_text if history_text else 'No previous conversation',
                user_input=request.payload.content,
                thought=reasoning['thought'],
                plan=', '.join(reasoning['plan']),
                action_type=reasoning['action_type'],
            )
        else:
            user_prompt = ACTING_USER_TEMPLATE_NO_DATA.format(
                conversation_history=history_text if history_text else 'No previous conversation',
                user_input=request.payload.content,
                thought=reasoning['thought'],
                plan=', '.join(reasoning['plan']),
                action_type=reasoning['action_type'],
            )

        try:
            # AI generates the response
            response_text = await invoke_llm(ACTING_SYSTEM_PROMPT, user_prompt)
            return {
                'user_message': response_text,
                'reasoning': reasoning['thought'],
                'action_taken': reasoning['action_type'],
            }
        except Exception as exc:
            # Fallback response if LLM fails
            return {
                'user_message': "I'm here to help! I can generate Minutes of Meeting, extract action items, answer questions, and more. What would you like to do?",
                'reasoning': f"LLM call failed: {exc}. Using fallback response.",
                'action_taken': 'fallback',
            }
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct Step 3: Observation
        Verify the response is appropriate and complete.
        """
        response_text = action_result.get('user_message', '')
        
        # Check if response is meaningful
        is_complete = len(response_text) > 10
        
        return {
            'observation': f"Generated response with {len(response_text)} characters. Action: {action_result.get('action_taken')}",
            'is_complete': is_complete,
            'next_step': None if is_complete else 'retry_with_different_prompt',
        }

    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """
        Main execution using ReAct pattern:
        1. Reason about the request (AI-driven)
        2. Act based on reasoning (AI-driven)
        3. Observe the results
        """
        # Step 1: Reasoning (AI decides strategy)
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        # Step 2: Acting (AI generates response)
        action_result = await self._act(request, reasoning)
        
        # Step 3: Observation (verify completion)
        observation = await self._observe(request, action_result)
        
        # Build final response with full ReAct trace
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Plan] {', '.join(reasoning['plan'])}\n"
            f"[Action] {action_result.get('action_taken', 'unknown')}\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={"user_message": action_result['user_message']},
            confidence=reasoning.get('confidence', 0.95),
            reasoning=full_reasoning,
        )

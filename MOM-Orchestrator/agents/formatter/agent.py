"""Formatter Agent - AI-Driven with ReAct Pattern"""
from __future__ import annotations
import json
from typing import Dict, Any
from llm.bedrock_client import invoke_llm_json
from schemas.contracts import AgentRequest, AgentResponse
from agents.base_agent import BaseAgent
from formats.registry import get_format, get_default_format
from .prompts import (
    REASONING_SYSTEM_PROMPT,
    REASONING_USER_TEMPLATE,
    ACTING_SYSTEM_PROMPT,
    ACTING_USER_TEMPLATE,
)


class FormatterAgent(BaseAgent):
    name = "formatter"
    
    async def _reason(self, request: AgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI analyzes data and plans formatting strategy"""
        data = request.context.intermediate_data
        format_id = data.get("format_id", "standard")
        
        # Get format template
        fmt = get_format(format_id) or get_default_format()
        
        topics = data.get("topics", [])
        decisions = data.get("decisions", [])
        actions = data.get("actions", [])
        
        user_prompt = REASONING_USER_TEMPLATE.format(
            num_topics=len(topics),
            num_decisions=len(decisions),
            num_actions=len(actions),
            format_id=format_id,
            format_sections=", ".join(fmt.get("sections", [])),
        )
        
        try:
            result = await invoke_llm_json(REASONING_SYSTEM_PROMPT, user_prompt)
            return {
                'thought': result.get('thought', 'Planning formatting'),
                'formatting_strategy': result.get('formatting_strategy', 'standard'),
                'section_order': result.get('section_order', fmt.get("sections", [])),
                'confidence': result.get('confidence', 0.9),
                'plan': result.get('plan', ['Format MOM']),
                'should_act': True,
                'format_template': fmt,
            }
        except Exception as exc:
            return {
                'thought': f'AI reasoning failed: {exc}',
                'formatting_strategy': 'standard',
                'section_order': fmt.get("sections", []),
                'confidence': 0.8,
                'plan': ['Format with fallback'],
                'should_act': True,
                'format_template': fmt,
            }
    
    async def _act(self, request: AgentRequest, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """AI formats the MOM based on reasoning - STANDARD FORMATS ONLY"""
        data = request.context.intermediate_data
        
        topics = data.get("topics", [])
        decisions = data.get("decisions", [])
        actions = data.get("actions", [])
        
        # Check if custom template structure exists
        fmt = reasoning['format_template']
        format_id = fmt.get('id', 'standard')
        template_structure = fmt.get('template_structure')
        
        print(f"[FORMATTER DEBUG] format_id: {format_id}")
        print(f"[FORMATTER DEBUG] template_structure type: {type(template_structure)}")
        print(f"[FORMATTER DEBUG] template_structure value: {template_structure}")
        print(f"[FORMATTER DEBUG] has sections: {template_structure.get('sections') if template_structure else None}")
        
        # Synthesize template structure for built-in formats if it doesn't exist
        if not template_structure or not template_structure.get('sections'):
            sections = []
            custom_labels = fmt.get('custom_labels', {})
            
            # Use the defined sections from the format config
            for sec_key in fmt.get('sections', ['topics', 'decisions', 'actions']):
                label = custom_labels.get(sec_key, sec_key.replace('_', ' ').title())
                sections.append({'id': sec_key, 'label': label, 'type': 'header'})
            
            template_structure = {'sections': sections}
        
        # For custom templates with sections, use AI to map data
        # Format data for prompt
        topics_str = "\n".join([f"- {t.get('title', '')}: {t.get('summary', '')}" for t in topics[:10]])
        decisions_str = "\n".join([f"- {d.get('decision', '')} (Owner: {d.get('owner', 'N/A')})" for d in decisions[:10]])
        actions_str = "\n".join([f"- {a.get('task', '')} (Owner: {a.get('owner', 'TBD')}, Deadline: {a.get('deadline', 'N/A')})" for a in actions[:10]])
        
        # Build custom template instructions with detailed field mapping
        sections_info = []
        field_mapping_examples = []
        
        for section in template_structure['sections']:
            section_id = section['id']
            section_label = section['label']
            section_type = section.get('type', 'unknown')
            fields = template_structure.get('fields', {}).get(section_id, [])
            
            # Build section description
            if fields:
                field_details = []
                for f in fields:
                    field_id = f.get('id', f.get('name', '').lower().replace(' ', '_'))
                    field_label = f.get('label', f.get('name', 'Unknown'))
                    field_type = f.get('type', 'text')
                    field_details.append(f"'{field_id}' (label: '{field_label}', type: {field_type})")
                
                fields_str = ", ".join(field_details)
                sections_info.append(f"- Section '{section_id}' (label: '{section_label}', type: {section_type}): Fields: {fields_str}")
                
            if fields:
                # Add example for this section
                if section_type == 'metadata':
                    # For metadata, use section_id directly as key with string value
                    field_mapping_examples.append(f"    \"{section_id}\": \"value for {section_label}\"")
                else:
                    # For other sections (headers/tables), create a LIST of objects
                    example_fields = {f.get('id', f.get('name', '').lower().replace(' ', '_')): "value" for f in fields[:3]}
                    field_mapping_examples.append(f"    \"{section_id}\": [\n      {json.dumps(example_fields)},\n      {json.dumps(example_fields)}\n    ]")
            else:
                sections_info.append(f"- Section '{section_id}' (label: '{section_label}', type: {section_type}): Use section_id as key with string value")
                field_mapping_examples.append(f"    \"{section_id}\": \"value for {section_label}\"")
        
        example_structure = "{\n  \"sections\": {\n" + ",\n".join(field_mapping_examples) + "\n  }\n}"
        
        custom_instructions = f"""
CRITICAL: This is a CUSTOM TEMPLATE. You MUST follow these structural rules exactly.

Template Structure (USE THESE EXACT FIELD IDs):
{chr(10).join(sections_info)}

MANDATORY DATA FORMATTING RULES:
1. NO AGGREGATION: NEVER join multiple items into one string (NO "Row 1: ...", NO "1, 2, 3").
2. TABLE DATA: For sections with multiple fields (Agenda, Actions, etc.), output a JSON LIST of objects.
3. FIELD NAMES: Use ONLY the exact field IDs listed above for the keys in your objects.
4. NO PLACEHOLDERS: NEVER use example dates (e.g. 3/23/2026) or "Row 1" text from the template if not in the transcript.
5. EMPTY DATA: If the transcript doesn't have data for a field, use "" or "N/A". NEVER guess.
6. METADATA: For single fields (Date, Time, Location), use a simple string value.
7. NESTED OBJECTS: ALL field values MUST be plain strings or numbers - NEVER another nested object.

EXAMPLE OUTPUT STRUCTURE:
{example_structure}

DATA MAPPING:
- Use topics list to fill Agenda/Discussion sections (map 1 topic -> 1 object in the list).
- Use actions list to fill Action Points sections (map 1 action -> 1 object in the list).
- Use decisions list to fill Decision sections.
"""

        
        user_prompt = ACTING_USER_TEMPLATE.format(
            topics=topics_str or "No topics",
            decisions=decisions_str or "No decisions",
            actions=actions_str or "No actions",
            format_id=fmt.get('id', 'standard'),
            format_sections=", ".join(reasoning['section_order']),
            formatting_strategy=reasoning['formatting_strategy'],
            custom_template_instructions=custom_instructions,
        )
        
        print(f"[FORMATTER DEBUG] ===== CUSTOM TEMPLATE INSTRUCTIONS =====")
        print(custom_instructions)
        print(f"[FORMATTER DEBUG] ===== END INSTRUCTIONS =====")
        
        try:
            formatted = await invoke_llm_json(ACTING_SYSTEM_PROMPT, user_prompt)
            
            # CRITICAL: Validate and clean the AI output
            sections_output = formatted.get("sections", {})
            cleaned_sections = {}
            
            # Helper: clean a single primitive value
            def _clean_val(val) -> str:
                if val in (None, "N/A", "None", ""):
                    return "N/A"
                return str(val).strip()

            # Helper: flatten any value to a human-readable string (fallback)
            def _flatten(val) -> str:
                if val is None:
                    return "N/A"
                if isinstance(val, str):
                    s = val.strip()
                    return s if s and s.lower() != "n/a" else "N/A"
                if isinstance(val, (int, float, bool)):
                    return str(val)
                if isinstance(val, list):
                    # For lists of strings/numbers, join with |
                    parts = []
                    for item in val:
                        if isinstance(item, dict):
                            # Fallback flatten for dict inside list
                            parts.append(", ".join(f"{v}" for v in item.values() if not isinstance(v, (dict, list))))
                        else:
                            parts.append(str(item))
                    return " | ".join(p for p in parts if p and p != "N/A") or "N/A"
                if isinstance(val, dict):
                    # Try common value keys first
                    for key in ("value", "text", "content", "data"):
                        if key in val and isinstance(val[key], (str, int, float)):
                            return _clean_val(val[key])
                    # Flatten all non-nested entries
                    parts = [f"{v}" for v in val.values() if isinstance(v, (str, int, float)) and v not in (None, "", "N/A")]
                    return ", ".join(parts) if parts else "N/A"
                return str(val)

            # Generic placeholder keys the LLM sometimes uses wrongly
            GENERIC_KEYS = {"label", "field_name", "another_field", "list_field", "value"}

            for section_id, section_data in sections_output.items():
                if isinstance(section_data, list):
                    # ── TABLE DATA ──
                    # Keep lists of dicts as-is (they will be rendered as tables in frontend)
                    cleaned_list = []
                    for item in section_data:
                        if isinstance(item, dict):
                            # Clean the dict fields
                            cleaned_item = {k: _flatten(v) for k, v in item.items()}
                            # Only add if it has at least one non-N/A value
                            if any(v != "N/A" for v in cleaned_item.values()):
                                cleaned_list.append(cleaned_item)
                        else:
                            cleaned_list.append(_clean_val(item))
                    cleaned_sections[section_id] = cleaned_list if cleaned_list else "N/A"

                elif isinstance(section_data, dict):
                    # ── METADATA OR FIELD-MAP ──
                    if any(key in section_data for key in GENERIC_KEYS):
                        # Improper metadata object: extract best primitive
                        for probe in ("value", "field_name", "text", "content"):
                            if probe in section_data and section_data[probe] not in (None, "N/A", ""):
                                cleaned_sections[section_id] = _clean_val(section_data[probe])
                                break
                        else:
                            cleaned_sections[section_id] = "N/A"
                    else:
                        # Proper field-map: clean each value but keep dict structure
                        cleaned_fields = {}
                        for field_id, field_value in section_data.items():
                            cleaned_fields[field_id] = _flatten(field_value)
                        cleaned_sections[section_id] = cleaned_fields
                else:
                    # ── SIMPLE VALUE ──
                    cleaned_sections[section_id] = _flatten(section_data)

            
            print(f"[FORMATTER DEBUG] Original sections: {sections_output}")
            print(f"[FORMATTER DEBUG] Cleaned sections: {cleaned_sections}")
            
            # Build structured MOM with cleaned sections
            structured_mom = {
                "title": formatted.get("title", "Minutes of Meeting"),
                "format_name": fmt.get('name', 'Standard MOM'),
                "metadata": formatted.get("metadata", {}),
                "topics": topics,
                "decisions": decisions,
                "actions": actions,
                "format_id": fmt.get('id'),
                "sections": cleaned_sections,
                "template_structure": template_structure,
            }
            
            return {
                'structured_mom': structured_mom,
                'formatting_method': reasoning['formatting_strategy'],
            }
        except Exception as exc:
            # Fallback: simple structure
            return {
                'structured_mom': {
                    "title": "Minutes of Meeting",
                    "format_name": fmt.get('name', 'Standard MOM'),
                    "topics": topics,
                    "decisions": decisions,
                    "actions": actions,
                    "format_id": fmt.get('id'),
                },
                'formatting_method': f'fallback: {exc}',
            }
    
    async def _observe(self, request: AgentRequest, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify formatting quality"""
        mom = action_result.get('structured_mom', {})
        return {
            'observation': f"Formatted MOM with {len(mom.get('topics', []))} topics, {len(mom.get('decisions', []))} decisions, {len(mom.get('actions', []))} actions",
            'is_complete': True,
            'next_step': None,
        }
    
    async def _execute(self, request: AgentRequest) -> AgentResponse:
        """Execute ReAct pattern for formatting"""
        reasoning = await self._reason(request, request.context.intermediate_data)
        
        if not reasoning['should_act']:
            return self.fail(session_id=request.session_id, reasoning="No data to format")
        
        action_result = await self._act(request, reasoning)
        observation = await self._observe(request, action_result)
        
        full_reasoning = (
            f"[Reasoning] {reasoning['thought']}\n"
            f"[Plan] {', '.join(reasoning['plan'])}\n"
            f"[Action] {action_result.get('formatting_method')}\n"
            f"[Observation] {observation['observation']}"
        )
        
        return self.success(
            session_id=request.session_id,
            output={"structured_mom": action_result['structured_mom']},
            confidence=reasoning['confidence'],
            reasoning=full_reasoning,
        )

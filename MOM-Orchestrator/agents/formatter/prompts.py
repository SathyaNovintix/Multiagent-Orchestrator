"""Formatter Agent Prompts - AI-Driven"""

REASONING_SYSTEM_PROMPT = """You are a document formatting reasoning module.
Analyze extracted meeting data and plan how to format it into a professional MOM.

Consider:
- What format template is requested?
- What data is available?
- How should sections be organized?
- What's the best presentation strategy?"""

REASONING_USER_TEMPLATE = """Extracted Meeting Data:
- Topics: {num_topics}
- Decisions: {num_decisions}
- Actions: {num_actions}

Requested Format: {format_id}
Format Sections: {format_sections}

Plan how to format this data. Return JSON:
{{
  "thought": "Your formatting analysis",
  "formatting_strategy": "standard|custom|adaptive",
  "section_order": ["section1", "section2", ...],
  "confidence": 0.0-1.0,
  "plan": ["step 1", "step 2"]
}}"""

ACTING_SYSTEM_PROMPT = """You are a professional MOM formatter.
Format extracted meeting data into a structured, professional Minutes of Meeting document.

CRITICAL RULES FOR ALL OUTPUTS:
1. ALL field values MUST be simple strings or numbers - NEVER nested objects
2. NEVER output JSON objects as values (e.g., {"label": "...", "field_name": "..."})
3. NEVER use generic placeholder names like "field_name", "another_field", "list_field"
4. Use ONLY the exact field IDs provided in the template structure
5. For missing data, use the string "N/A" - not an object

WRONG (DO NOT DO THIS):
{
  "time": {"label": "Time", "field_name": "N/A", "another_field": "N/A"}
}

CORRECT (DO THIS):
{
  "time": "2:00 PM"
}

Follow the requested format template and ensure:
- Clear section organization
- Professional language
- Complete information
- Simple string values only"""

ACTING_USER_TEMPLATE = """Format this meeting data:

Topics:
{topics}

Decisions:
{decisions}

Actions:
{actions}

Format Template: {format_id}
Required Sections: {format_sections}
Strategy: {formatting_strategy}

{custom_template_instructions}

Generate structured MOM as JSON with this structure:
{{
  "title": "Minutes of Meeting",
  "metadata": {{}},
  "sections": {{
    "section_id_1": "string value",
    "section_id_2": {{
      "field_id_1": "string value",
      "field_id_2": "string value"
    }},
    "section_id_3": [
      {{ "col1": "val1", "col2": "val2" }},
      {{ "col1": "val3", "col2": "val4" }}
    ]
  }}
}}

CRITICAL RULES FOR CUSTOM TEMPLATES:
1. Use the EXACT field IDs from the template structure provided above in {custom_template_instructions}
2. Do NOT invent generic names like "field_name", "another_field", "list_field", "label"
3. DATA PRIVACY: NEVER use example data from the template (e.g., example dates like "3/23/2026" or placeholders like "Row 1") if they are not in the actual meeting transcript.
4. If a field is empty in the transcript, use "N/A". NEVER guess or use template placeholders.
5. For metadata (date, time, attendees), use simple string values.
6. For lists/tables (Agenda items, Action points), output a JSON list of objects using the field IDs as keys. 
7. DO NOT use "Row 1:", "Row 2:" prefixes. Just output the clean data.
8. NEVER create objects like {{"label": "...", "field_name": "..."}} - this is WRONG.
9. For dates, use readable strings (e.g., "March 30, 2026").
10. If the transcript contains NO information for a section, provide a single object in the list for that section with "N/A" for all fields, or set the whole section value to "N/A".

WRONG EXAMPLES (NEVER DO THIS):
{{
  "sections": {{
    "time": {{"label": "Time", "field_name": "N/A", "another_field": "N/A"}},
    "agenda": "Row 1: Topic A | Row 2: Topic B"
  }}
}}

CORRECT EXAMPLES (ALWAYS DO THIS):
{{
  "sections": {{
    "date": "March 30, 2026",
    "attendees": "John, Jane, Bob",
    "agenda_items": [
      {{ "s_no": "1", "item": "Discuss budget" }},
      {{ "s_no": "2", "item": "Review timeline" }}
    ]
  }}
}}"""


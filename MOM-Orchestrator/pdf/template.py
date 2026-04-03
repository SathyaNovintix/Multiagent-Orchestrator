"""
MOM HTML Template — AgentMesh AI
Renders the MOM document using the selected format's colors and labels.
Supports custom template structures from uploaded Excel/Word/CSV files.
"""
from __future__ import annotations
from schemas.contracts import MOMDocument


def _safe_str(val) -> str:
    """Convert any value to a clean human-readable string (no raw JSON)."""
    if val is None:
        return "N/A"
    if isinstance(val, str):
        return val if val.strip() else "N/A"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, dict):
                parts.append(", ".join(f"{k}: {v}" for k, v in item.items() if not isinstance(v, (dict, list))))
            else:
                parts.append(str(item))
        return " | ".join(parts) if parts else "N/A"
    if isinstance(val, dict):
        for key in ("value", "text", "content", "data"):
            if key in val and isinstance(val[key], (str, int, float)):
                return str(val[key]) if val[key] is not None else "N/A"
        parts = [f"{k}: {v}" for k, v in val.items() if isinstance(v, (str, int, float)) and v not in (None, "")]
        return ", ".join(parts) if parts else "N/A"
    return str(val)


def _render_custom_sections_html(mom: MOMDocument, template_structure: dict, accent: str) -> str:
    """Render custom template sections as professional HTML."""
    html = ""
    sections_meta = template_structure.get("sections", [])
    fields_meta = template_structure.get("fields", {})
    mom_sections: dict = getattr(mom, "sections", None) or {}

    for section in sections_meta:
        section_id = section.get("id", "")
        section_label = section.get("label", section_id)
        section_data = mom_sections.get(section_id)

        # Skip sections with no data
        if section_data is None:
            continue

        # Fields defined for this section
        fields = fields_meta.get(section_id, [])

        rows_html = ""

        if isinstance(section_data, dict) and not any(
            k in section_data for k in ("label", "field_name", "another_field", "list_field")
        ):
            # It's a proper field-map dict
            if fields:
                # Render in template field order
                for f in fields:
                    fid = f.get("id") or f.get("name", "").lower().replace(" ", "_")
                    flabel = f.get("label") or f.get("name") or fid
                    fval = _safe_str(section_data.get(fid))
                    rows_html += f"""
                        <div class="kv-row">
                            <div class="kv-label">{flabel}</div>
                            <div class="kv-value">{fval}</div>
                        </div>"""
            else:
                # No field metadata — render all key-value pairs
                for k, v in section_data.items():
                    display_key = k.replace("_", " ").title()
                    rows_html += f"""
                        <div class="kv-row">
                            <div class="kv-label">{display_key}</div>
                            <div class="kv-value">{_safe_str(v)}</div>
                        </div>"""
        else:
            # Metadata / simple string value
            val_str = _safe_str(section_data)
            rows_html += f"""
                <div class="kv-row">
                    <div class="kv-label">{section_label}</div>
                    <div class="kv-value">{val_str}</div>
                </div>"""

        html += f"""
        <div class="section">
            <div class="section-title">{section_label}</div>
            <div class="kv-container">{rows_html}</div>
        </div>"""

    return html


def render_mom_html(
    mom: MOMDocument,
    title: str = "Minutes of Meeting",
    fmt: dict | None = None,
) -> str:
    """
    Renders MOM to HTML using the format definition (colors, labels, sections).
    Falls back to standard format if fmt is None.
    Supports custom template structures from uploaded Excel/Word files.
    """
    fmt = fmt or {}
    accent = fmt.get("accent_color", "#e6a817")
    header_bg = fmt.get("header_color", "#1a1a2e")
    labels = dict(fmt.get("custom_labels") or {})
    sections = fmt.get("sections", ["topics", "decisions", "actions"])

    # Check if there's a custom template structure
    template_structure = fmt.get("template_structure")
    if template_structure and template_structure.get("sections"):
        # Use template-defined section labels
        for section in template_structure["sections"]:
            if section["id"] not in labels:
                labels[section["id"]] = section["label"]

    topic_label = labels.get("topics", "Discussion Topics")
    decision_label = labels.get("decisions", "Decisions")
    action_label = labels.get("actions", "Action Items")

    sections_html = ""

    # ── Custom template rendering ───────────────────────────────────────────
    if template_structure and template_structure.get("sections"):
        sections_html = _render_custom_sections_html(mom, template_structure, accent)
        # Also append standard sections if they have data and aren't covered by the template
        template_section_ids = {s["id"] for s in template_structure["sections"]}
        if "topics" not in template_section_ids and mom.topics:
            topics_html = "".join(
                f"""<div class="item">
                    <div class="item-title">{t.get('title','')}</div>
                    <div class="item-body">{t.get('summary','')}</div>
                    {f'<div class="ts">⏱ {t["timestamp"]}</div>' if t.get('timestamp') else ''}
                </div>"""
                for t in mom.topics
            ) or "<p class='empty'>None recorded.</p>"
            sections_html += f'<div class="section"><div class="section-title">{topic_label}</div>{topics_html}</div>'
        if "decisions" not in template_section_ids and mom.decisions:
            decisions_html = "".join(
                f"""<div class="item">
                    <div class="item-body">{d.get('decision','')}</div>
                    <div class="meta"><span class="badge">{d.get('owner','N/A')}</span>
                    {f'<span class="badge cond">{d["condition"]}</span>' if d.get('condition') else ''}
                    </div></div>"""
                for d in mom.decisions
            ) or "<p class='empty'>None recorded.</p>"
            sections_html += f'<div class="section"><div class="section-title">{decision_label}</div>{decisions_html}</div>'
        if "actions" not in template_section_ids and mom.actions:
            priority_color = {"high": "#c53030", "medium": "#c05621", "low": "#276749"}
            priority_bg = {"high": "#fff5f5", "medium": "#fffaf0", "low": "#f0fff4"}
            actions_html = "".join(
                f"""<div class="item">
                    <div class="item-body">{a.get('task','')}</div>
                    <div class="meta">
                        <span class="badge">{a.get('owner','TBD')}</span>
                        {f'<span class="badge">📅 {a["deadline"]}</span>' if a.get('deadline') else ''}
                        <span class="badge" style="color:{priority_color.get(a.get('priority','medium'),'')};
                            background:{priority_bg.get(a.get('priority','medium'),'')}">
                            {(a.get('priority') or 'medium').capitalize()}
                        </span>
                        {' <span class="badge warn">⚠ Ambiguous</span>' if a.get('ambiguous') else ''}
                    </div></div>"""
                for a in mom.actions
            ) or "<p class='empty'>None recorded.</p>"
            sections_html += f'<div class="section"><div class="section-title">{action_label}</div>{actions_html}</div>'

    else:
        # ── Standard rendering ──────────────────────────────────────────────
        if "topics" in sections and mom.topics:
            topics_html = "".join(
                f"""<div class="item">
                    <div class="item-title">{t.get('title','')}</div>
                    <div class="item-body">{t.get('summary','')}</div>
                    {f'<div class="ts">⏱ {t["timestamp"]}</div>' if t.get('timestamp') else ''}
                </div>"""
                for t in mom.topics
            ) or "<p class='empty'>None recorded.</p>"
            sections_html += f'<div class="section"><div class="section-title">{topic_label}</div>{topics_html}</div>'

        if "decisions" in sections and mom.decisions:
            decisions_html = "".join(
                f"""<div class="item">
                    <div class="item-body">{d.get('decision','')}</div>
                    <div class="meta">
                        <span class="badge">{d.get('owner','N/A')}</span>
                        {f'<span class="badge cond">{d["condition"]}</span>' if d.get('condition') else ''}
                    </div>
                </div>"""
                for d in mom.decisions
            ) or "<p class='empty'>None recorded.</p>"
            sections_html += f'<div class="section"><div class="section-title">{decision_label}</div>{decisions_html}</div>'

        if "actions" in sections and mom.actions:
            priority_color = {"high": "#c53030", "medium": "#c05621", "low": "#276749"}
            priority_bg = {"high": "#fff5f5", "medium": "#fffaf0", "low": "#f0fff4"}
            actions_html = "".join(
                f"""<div class="item">
                    <div class="item-body">{a.get('task','')}</div>
                    <div class="meta">
                        <span class="badge">{a.get('owner','TBD')}</span>
                        {f'<span class="badge">📅 {a["deadline"]}</span>' if a.get('deadline') else ''}
                        <span class="badge" style="color:{priority_color.get(a.get('priority','medium'),'')};
                            background:{priority_bg.get(a.get('priority','medium'),'')}">
                            {(a.get('priority') or 'medium').capitalize()}
                        </span>
                        {' <span class="badge warn">⚠ Ambiguous</span>' if a.get('ambiguous') else ''}
                    </div>
                </div>"""
                for a in mom.actions
            ) or "<p class='empty'>None recorded.</p>"
            sections_html += f'<div class="section"><div class="section-title">{action_label}</div>{actions_html}</div>'

    participants = ", ".join(mom.participants) if mom.participants else "Not specified"
    lang_note = (
        f"Original: <strong>{mom.original_language.upper()}</strong> → English"
        if mom.original_language not in ("en", "english") else "Language: <strong>English</strong>"
    )
    format_name = fmt.get("name", "Standard MOM")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 13px;
          color: #1a1a2e; background: #fff; padding: 40px; }}
  .header {{ background: {header_bg}; color: #fff; padding: 28px 32px;
             border-radius: 8px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; }}
  .header .sub {{ font-size: 12px; color: #a0aec0; margin-top: 6px; }}
  .header .fmt-badge {{ display: inline-block; background: {accent}; color: {header_bg};
                        border-radius: 4px; padding: 3px 10px; font-size: 11px;
                        font-weight: 700; margin-top: 10px; }}
  .meta-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .meta-box {{ background: #f7f8fc; border-radius: 6px; padding: 12px 16px; flex: 1; min-width: 140px; }}
  .meta-box .label {{ font-size: 10px; text-transform: uppercase; color: #718096;
                      letter-spacing: 0.8px; margin-bottom: 4px; }}
  .meta-box .value {{ font-size: 13px; font-weight: 600; color: #2d3748; }}
  .section {{ margin-bottom: 28px; }}
  .section-title {{ font-size: 13px; font-weight: 700; color: {header_bg};
                    border-left: 4px solid {accent}; padding-left: 10px;
                    margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .item {{ background: #f7f8fc; border-radius: 6px; padding: 12px 16px;
           margin-bottom: 8px; border-left: 3px solid #e2e8f0; }}
  .item-title {{ font-weight: 600; margin-bottom: 4px; color: #2d3748; }}
  .item-body {{ color: #4a5568; line-height: 1.5; }}
  .ts {{ font-size: 11px; color: #a0aec0; margin-top: 4px; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .badge {{ font-size: 11px; background: #edf2f7; color: #4a5568;
            border-radius: 4px; padding: 2px 8px; }}
  .cond {{ background: #ebf4ff; color: #3182ce; }}
  .warn {{ background: #fff5f5; color: #e53e3e; }}
  .empty {{ color: #a0aec0; font-style: italic; font-size: 12px; }}
  .footer {{ margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 12px;
             font-size: 11px; color: #a0aec0; text-align: center; }}
  /* Custom template key-value styles */
  .kv-container {{ display: flex; flex-direction: column; gap: 6px; }}
  .kv-row {{ display: flex; gap: 0; background: #f7f8fc; border-radius: 6px;
             border-left: 3px solid {accent}; overflow: hidden; }}
  .kv-label {{ font-size: 11px; font-weight: 700; color: #718096; text-transform: uppercase;
               letter-spacing: 0.5px; padding: 10px 14px; min-width: 160px;
               background: #edf2f7; border-right: 1px solid #e2e8f0; flex-shrink: 0; }}
  .kv-value {{ padding: 10px 14px; color: #2d3748; font-size: 13px; line-height: 1.5; flex: 1; }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <div class="sub">Generated by AgentMesh AI &nbsp;|&nbsp; {mom.created_at[:10]}</div>
  <div class="fmt-badge">{format_name}</div>
</div>

<div class="meta-row">
  <div class="meta-box">
    <div class="label">Session</div>
    <div class="value">{mom.session_id[:8]}…</div>
  </div>
  <div class="meta-box">
    <div class="label">Participants</div>
    <div class="value">{participants}</div>
  </div>
  <div class="meta-box">
    <div class="label">Language</div>
    <div class="value">{mom.original_language.upper()}</div>
  </div>
  <div class="meta-box">
    <div class="label">Topics / Decisions / Actions</div>
    <div class="value">{len(mom.topics)} / {len(mom.decisions)} / {len(mom.actions)}</div>
  </div>
</div>

{sections_html}

<div class="footer">
  {lang_note} &nbsp;|&nbsp; AgentMesh AI v1.0 &nbsp;|&nbsp; {format_name} &nbsp;|&nbsp; Confidential
</div>
</body>
</html>"""

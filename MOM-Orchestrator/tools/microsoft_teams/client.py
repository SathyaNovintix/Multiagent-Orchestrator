"""
Microsoft Teams Client

Sends MOM documents to Microsoft Teams channels using Incoming Webhooks or Power Automate.
"""
import httpx
from datetime import datetime
from typing import Optional, Dict, Any


class TeamsClient:
    """Client for sending messages to Microsoft Teams via webhook."""
    
    def __init__(self, webhook_url: str):
        """
        Initialize Teams client with webhook URL.
        
        Args:
            webhook_url: Microsoft Teams Incoming Webhook URL or Power Automate URL
        """
        self.webhook_url = webhook_url
        self.is_power_automate = "powerplatform.com" in webhook_url or "powerautomate" in webhook_url
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to Teams channel.
        
        Args:
            message: Already formatted payload (from format_mom_for_teams)
            
        Returns:
            Response from Teams API
        """
        async with httpx.AsyncClient() as client:
            print(f"[Teams] Sending payload to {'Power Automate' if self.is_power_automate else 'Classic Webhook'}")
            
            response = await client.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"[Teams] Response status: {response.status_code}")
            
            response.raise_for_status()
            return {"status": "success", "message": "Sent to Teams"}


def format_mom_for_teams(mom_data: Dict[str, Any], download_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Format MOM data as Microsoft Teams Adaptive Card.
    
    Args:
        mom_data: Structured MOM data
        download_url: Optional URL to download full MOM
        
    Returns:
        Teams message payload with Adaptive Card
    """
    topics = mom_data.get("topics", [])
    decisions = mom_data.get("decisions", [])
    actions = mom_data.get("actions", [])
    
    # Extract unique participants from multiple sources
    participants = set()
    
    # 1. Check if there's a direct participants list in the MOM data
    if mom_data.get("participants"):
        if isinstance(mom_data["participants"], list):
            participants.update(p for p in mom_data["participants"] if p and p not in ['N/A', 'Not specified'])
            print(f"[Teams] Found direct participants: {mom_data['participants']}")
    
    # 2. Extract from custom template sections (for custom templates)
    sections = mom_data.get("sections", {})
    if sections:
        print(f"[Teams] Checking custom template sections: {list(sections.keys())}")
        for section_id, section_data in sections.items():
            # Check for attendees/participants fields
            if section_id.lower() in ['attendees', 'participants', 'meeting_info']:
                if isinstance(section_data, dict):
                    attendees = section_data.get('attendees') or section_data.get('participants')
                    if attendees and attendees not in ['N/A', 'Not specified']:
                        if isinstance(attendees, str):
                            # Split comma-separated names
                            names = [n.strip() for n in attendees.split(',')]
                            participants.update(n for n in names if n and n not in ['N/A', 'Not specified'])
                            print(f"[Teams] Found participants in {section_id}: {names}")
                        elif isinstance(attendees, list):
                            participants.update(attendees)
                            print(f"[Teams] Found participants in {section_id}: {attendees}")
            
            # Extract from action items in custom sections
            if isinstance(section_data, list):
                for item in section_data:
                    if isinstance(item, dict):
                        # Check various owner field names
                        for owner_field in ['responsible_person', 'owner', 'assigned_to', 'assignee']:
                            owner = item.get(owner_field)
                            if owner and owner not in ['TBD', 'Unassigned', 'N/A', 'Not specified', 'Team']:
                                participants.add(owner)
                                print(f"[Teams] Found participant from {section_id}.{owner_field}: {owner}")
    
    # 3. From standard topics (each topic may have participants list)
    for topic in topics:
        if isinstance(topic, dict):
            if topic.get('participants'):
                if isinstance(topic['participants'], list):
                    participants.update(topic['participants'])
                    print(f"[Teams] Found participants in topic: {topic['participants']}")
            # Also check summary/title for names (basic extraction)
            summary = topic.get('summary', '') or topic.get('title', '')
            if summary:
                # Look for common name patterns in the text
                import re
                # Match capitalized words that might be names
                potential_names = re.findall(r'\b([A-Z][a-z]+)\b', summary)
                for name in potential_names:
                    if len(name) > 2 and name not in ['The', 'This', 'That', 'There', 'When', 'Where', 'What', 'Who', 'How', 'Why']:
                        participants.add(name)
                        print(f"[Teams] Found potential participant in topic text: {name}")
    
    # 4. From standard action owners
    for action in actions:
        if isinstance(action, dict):
            owner = action.get('owner') or action.get('responsible_person')
            if owner and owner not in ['TBD', 'Unassigned', 'N/A', 'Not specified', 'Team']:
                participants.add(owner)
                print(f"[Teams] Found participant from action owner: {owner}")
    
    # 5. From standard decision owners
    for decision in decisions:
        if isinstance(decision, dict):
            owner = decision.get('owner')
            if owner and owner not in ['TBD', 'Unassigned', 'N/A', 'Not specified', 'Team']:
                participants.add(owner)
                print(f"[Teams] Found participant from decision owner: {owner}")
    
    print(f"[Teams] Total unique participants found: {participants}")
    
    # Build professional Adaptive Card body - CONCISE VERSION with proper spacing
    card_body = [
        # Header
        {
            "type": "TextBlock",
            "text": "📋 Meeting Minutes",
            "weight": "Bolder",
            "size": "ExtraLarge",
            "color": "Accent",
            "wrap": True
        },
        {
            "type": "TextBlock",
            "text": f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}",
            "size": "Small",
            "color": "Default",
            "spacing": "None",
            "isSubtle": True,
            "wrap": True
        },
        # Summary Stats
        {
            "type": "FactSet",
            "facts": [
                {"title": "👥 Participants", "value": str(len(participants)) if participants else "Not specified"},
                {"title": "📊 Topics", "value": str(len(topics))},
                {"title": "✅ Decisions", "value": str(len(decisions))},
                {"title": "🎯 Actions", "value": str(len(actions))}
            ],
            "spacing": "Medium",
            "separator": True
        }
    ]
    
    # Participants Section
    if participants:
        card_body.extend([
            {
                "type": "TextBlock",
                "text": "**Meeting Participants**",
                "weight": "Bolder",
                "size": "Medium",
                "spacing": "Large",
                "separator": True,
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": ", ".join(sorted(participants)),
                "wrap": True,
                "spacing": "Small"
            }
        ])
    
    # Topics Section - SHOW ALL
    if topics:
        card_body.extend([
            {
                "type": "TextBlock",
                "text": f"**📊 Discussion Topics** ({len(topics)})",
                "weight": "Bolder",
                "size": "Medium",
                "spacing": "Large",
                "separator": True,
                "wrap": True
            }
        ])
        
        for i, topic in enumerate(topics, 1):  # Show ALL topics
            title = topic.get('title') if isinstance(topic, dict) else str(topic)
            card_body.append({
                "type": "TextBlock",
                "text": f"• {title or 'Untitled'}",
                "wrap": True,
                "spacing": "Small"
            })
    
    # Decisions Section - SHOW ALL
    if decisions:
        card_body.extend([
            {
                "type": "TextBlock",
                "text": f"**✅ Key Decisions** ({len(decisions)})",
                "weight": "Bolder",
                "size": "Medium",
                "spacing": "Large",
                "separator": True,
                "wrap": True
            }
        ])
        
        for i, decision in enumerate(decisions, 1):  # Show ALL decisions
            decision_text = decision.get('decision') if isinstance(decision, dict) else str(decision)
            owner = decision.get('owner', 'Unassigned') if isinstance(decision, dict) else 'Unassigned'
            card_body.append({
                "type": "TextBlock",
                "text": f"• {decision_text}\n\n_Owner: {owner}_",
                "wrap": True,
                "spacing": "Small"
            })
    
    # Actions Section - SHOW ALL
    if actions:
        card_body.extend([
            {
                "type": "TextBlock",
                "text": f"**🎯 Action Items** ({len(actions)})",
                "weight": "Bolder",
                "size": "Medium",
                "spacing": "Large",
                "separator": True,
                "wrap": True
            }
        ])
        
        for i, action in enumerate(actions, 1):  # Show ALL actions
            if not isinstance(action, dict):
                continue
                
            priority = action.get('priority', 'medium').lower()
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
            
            task = action.get('task') or action.get('action_item', 'No task description')
            owner = action.get('owner') or action.get('responsible_person', 'Unassigned')
            deadline = action.get('deadline', 'Not specified')
            
            card_body.append({
                "type": "TextBlock",
                "text": f"{priority_emoji} {task}\n\n_Assigned: {owner} | Due: {deadline}_",
                "wrap": True,
                "spacing": "Small"
            })
    
    # Footer note
    card_body.extend([
        {
            "type": "TextBlock",
            "text": "💡 **Download full MOM (PDF/Excel) from the web application**",
            "size": "Small",
            "color": "Accent",
            "isSubtle": True,
            "wrap": True,
            "spacing": "Large",
            "separator": True
        }
    ])
    
    # Construct the Adaptive Card
    adaptive_card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": card_body
    }
    
    # No action buttons needed
    
    # Return in the format Power Automate expects
    return {
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": adaptive_card
            }
        ]
    }


async def send_mom_to_teams(
    webhook_url: str,
    mom_data: Dict[str, Any],
    download_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send MOM to Microsoft Teams channel.
    
    Args:
        webhook_url: Teams Incoming Webhook URL
        mom_data: Structured MOM data
        download_url: Optional URL to download full MOM
        
    Returns:
        Response from Teams API
    """
    client = TeamsClient(webhook_url)
    message = format_mom_for_teams(mom_data, download_url)
    return await client.send_message(message)



async def send_mom_to_teams_with_file(
    webhook_url: str,
    mom_data: Dict[str, Any],
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send MOM to Microsoft Teams channel with PDF file attachment.
    
    Note: Power Automate webhooks don't support file attachments directly.
    Instead, we'll include a note in the message that the PDF is available
    in the web app, and show all the MOM content in the card.
    
    Args:
        webhook_url: Teams webhook URL
        mom_data: Structured MOM data
        pdf_bytes: PDF file bytes (optional, not used with Power Automate)
        pdf_filename: PDF filename (optional, not used with Power Automate)
        
    Returns:
        Response from Teams API
    """
    client = TeamsClient(webhook_url)
    
    # For Power Automate webhooks, we can't attach files
    # So we just send the card with all the information
    message = format_mom_for_teams(mom_data, download_url=None)
    
    # Add a note about downloading from the web app
    card_body = message["attachments"][0]["content"]["body"]
    card_body.append({
        "type": "TextBlock",
        "text": "💡 To download the PDF, use the Download button in the web application.",
        "size": "Small",
        "color": "Accent",
        "isSubtle": True,
        "wrap": True,
        "spacing": "Medium",
        "separator": True
    })
    
    return await client.send_message(message)

"""
PM Tool Client — AgentMesh AI
HTTP client for integrating with external PM tool API.
"""
import os
import httpx
from typing import Optional


PM_TOOL_BASE_URL = os.getenv("PM_TOOL_BASE_URL", "https://pmo-novintix.onrender.com")
PM_TOOL_TIMEOUT = int(os.getenv("PM_TOOL_TIMEOUT", "30"))


async def send_to_pm_tool(session_id: str, message: str) -> dict:
    """
    Send action items to PM tool endpoint.
    
    Args:
        session_id: The PM tool session identifier
        message: The action items text to send
        
    Returns:
        dict: Response from PM tool API
        
    Raises:
        httpx.HTTPError: If the request fails
    """
    url = f"{PM_TOOL_BASE_URL}/chat"
    
    payload = {
        "session_id": session_id,
        "message": message
    }
    
    async with httpx.AsyncClient(timeout=PM_TOOL_TIMEOUT) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def format_action_items(actions: list) -> str:
    """
    Format action items into a readable message string.
    
    Args:
        actions: List of Action objects or dicts
        
    Returns:
        str: Formatted action items text
    """
    if not actions:
        return "No action items to assign."
    
    lines = ["Action Items:\n"]
    for i, action in enumerate(actions, 1):
        if isinstance(action, dict):
            task = action.get("task", "")
            owner = action.get("owner", "")
            deadline = action.get("deadline", "")
            priority = action.get("priority", "medium")
        else:
            task = getattr(action, "task", "")
            owner = getattr(action, "owner", "")
            deadline = getattr(action, "deadline", "")
            priority = getattr(action, "priority", "medium")
        
        lines.append(f"{i}. {task}")
        lines.append(f"   Owner: {owner}")
        if deadline:
            lines.append(f"   Deadline: {deadline}")
        lines.append(f"   Priority: {priority}")
        lines.append("")
    
    return "\n".join(lines)

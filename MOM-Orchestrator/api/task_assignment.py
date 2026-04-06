"""
Task Assignment Router — AgentMesh AI
Handles assignment of action items to external PM tool.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from storage.mongo_client import get_mom
from utils.pm_tool_client import send_to_pm_tool, format_action_items


router = APIRouter(prefix="/api/tasks", tags=["Task Assignment"])


class AssignTasksRequest(BaseModel):
    mom_id: str
    pm_session_id: Optional[str] = None
    custom_message: Optional[str] = None


class AssignTasksResponse(BaseModel):
    status: str
    message: str
    pm_response: Optional[dict] = None


@router.post("/assign", response_model=AssignTasksResponse)
async def assign_tasks_to_pm_tool(request: AssignTasksRequest):
    """
    Assign action items from a MOM to the PM tool.
    
    Args:
        mom_id: The MOM document ID containing action items
        pm_session_id: The PM tool session identifier (optional, defaults to mom_id)
        custom_message: Optional custom message (overrides auto-formatted actions)
        
    Returns:
        AssignTasksResponse with status and PM tool response
    """
    # Fetch MOM document
    mom = await get_mom(request.mom_id)
    if mom is None:
        raise HTTPException(status_code=404, detail="MOM not found")
    
    # Check if there are action items
    if not mom.actions and not request.custom_message:
        raise HTTPException(
            status_code=400,
            detail="No action items found in MOM and no custom message provided"
        )
    
    # Use mom_id as session_id if not provided
    pm_session_id = request.pm_session_id or request.mom_id
    
    # Format message
    if request.custom_message:
        message = request.custom_message
    else:
        message = format_action_items(mom.actions)
    
    # Send to PM tool
    try:
        pm_response = await send_to_pm_tool(
            session_id=pm_session_id,
            message=message
        )
        
        return AssignTasksResponse(
            status="success",
            message=f"Successfully assigned {len(mom.actions)} action items to PM tool",
            pm_response=pm_response
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send tasks to PM tool: {str(e)}"
        )

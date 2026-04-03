"""
Microsoft Teams API Router

FastAPI endpoints for Teams integration.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .client import send_mom_to_teams
from storage.mongo_client import get_mom


router = APIRouter(prefix="/api/teams", tags=["Microsoft Teams"])


class SendToTeamsRequest(BaseModel):
    mom_id: str


class SendToTeamsResponse(BaseModel):
    status: str
    message: str


@router.post("/send", response_model=SendToTeamsResponse)
async def send_mom_to_teams_endpoint(request: SendToTeamsRequest):
    """
    Send a MOM document to Microsoft Teams channel.
    Uses webhook URL from environment variable.
    
    Args:
        request: Contains mom_id
        
    Returns:
        Status of the send operation
    """
    # Get webhook URL from environment
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(
            status_code=500,
            detail="Teams webhook URL not configured. Please set TEAMS_WEBHOOK_URL in .env file."
        )
    
    # Fetch MOM from database
    mom = await get_mom(request.mom_id)
    if mom is None:
        raise HTTPException(status_code=404, detail="MOM not found")
    
    # Convert Pydantic models to dicts
    topics_data = [t.model_dump() if hasattr(t, 'model_dump') else t for t in mom.topics]
    decisions_data = [d.model_dump() if hasattr(d, 'model_dump') else d for d in mom.decisions]
    actions_data = [a.model_dump() if hasattr(a, 'model_dump') else a for a in mom.actions]
    
    # Prepare MOM data
    mom_data = {
        "topics": topics_data,
        "decisions": decisions_data,
        "actions": actions_data,
        "participants": mom.participants,
        "sections": mom.sections,
        "template_structure": mom.template_structure,
    }
    
    # Send to Teams (no download URL - users download from web app)
    try:
        result = await send_mom_to_teams(
            webhook_url=webhook_url,
            mom_data=mom_data,
            download_url=None  # No download button in Teams
        )
        return SendToTeamsResponse(
            status="success",
            message="MOM sent to Microsoft Teams successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send to Teams: {str(e)}"
        )

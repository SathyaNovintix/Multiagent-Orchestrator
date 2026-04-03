"""
Microsoft Teams Integration

Send MOM documents to Microsoft Teams channels via webhook.
"""
from .client import TeamsClient, send_mom_to_teams

__all__ = ["TeamsClient", "send_mom_to_teams"]

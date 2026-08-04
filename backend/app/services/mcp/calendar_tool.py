import httpx
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import select
from app.services.mcp.base_tool import BaseMCPTool
from app.schemas.mcp import ToolDefinition, ToolParameter
from app.models.user import User
from app.models.settings import OAuthAccount
from app.db.session import AsyncSessionLocal

class CalendarMCPTool(BaseMCPTool):
    """
    Google Calendar MCP Tool providing event management.
    """
    
    def __init__(self):
        self.base_url = "https://www.googleapis.com/calendar/v3/calendars/primary"

    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="calendar.list_events",
                description="List upcoming events from the user's primary calendar.",
                parameters=[
                    ToolParameter(name="max_results", type="integer", description="Maximum number of events to retrieve (default 10)", required=False)
                ]
            ),
            ToolDefinition(
                name="calendar.create_event",
                description="Create a new calendar event.",
                parameters=[
                    ToolParameter(name="summary", type="string", description="The title of the event.", required=True),
                    ToolParameter(name="start_time", type="string", description="ISO format start time (e.g. 2026-08-05T10:00:00Z)", required=True),
                    ToolParameter(name="end_time", type="string", description="ISO format end time (e.g. 2026-08-05T11:00:00Z)", required=True),
                    ToolParameter(name="description", type="string", description="Description of the event.", required=False)
                ]
            )
        ]

    async def _get_client(self, user: User) -> httpx.AsyncClient:
        """Helper to get an authenticated HTTP client for the user's Google account."""
        async with AsyncSessionLocal() as db:
            stmt = select(OAuthAccount).where(
                OAuthAccount.user_id == user.id,
                OAuthAccount.provider == "google"
            )
            result = await db.execute(stmt)
            oauth_account = result.scalars().first()
            
            if not oauth_account or not oauth_account.access_token:
                raise ValueError("User has not connected a Google account.")
                
            return httpx.AsyncClient(
                headers={"Authorization": f"Bearer {oauth_account.access_token}", "Content-Type": "application/json"}
            )

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user: User) -> Any:
        async with await self._get_client(user) as client:
            if tool_name == "calendar.list_events":
                return await self._list_events(client, arguments.get("max_results", 10))
            elif tool_name == "calendar.create_event":
                return await self._create_event(
                    client, 
                    arguments.get("summary"), 
                    arguments.get("start_time"), 
                    arguments.get("end_time"), 
                    arguments.get("description", "")
                )
            else:
                raise ValueError(f"Unknown Calendar tool: {tool_name}")

    async def _list_events(self, client: httpx.AsyncClient, max_results: int) -> Any:
        now = datetime.utcnow().isoformat() + 'Z'
        response = await client.get(
            f"{self.base_url}/events", 
            params={
                "maxResults": max_results,
                "timeMin": now,
                "singleEvents": "true",
                "orderBy": "startTime"
            }
        )
        response.raise_for_status()
        return response.json()

    async def _create_event(self, client: httpx.AsyncClient, summary: str, start_time: str, end_time: str, description: str) -> Any:
        if not all([summary, start_time, end_time]):
            raise ValueError("summary, start_time, and end_time are required")
            
        payload = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time
            },
            "end": {
                "dateTime": end_time
            }
        }
        response = await client.post(f"{self.base_url}/events", json=payload)
        response.raise_for_status()
        return response.json()

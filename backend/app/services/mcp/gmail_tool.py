import httpx
from typing import Dict, Any, List
import base64
from sqlalchemy import select
from app.services.mcp.base_tool import BaseMCPTool
from app.schemas.mcp import ToolDefinition, ToolParameter
from app.models.user import User
from app.models.settings import OAuthAccount
from app.db.session import AsyncSessionLocal

class GmailMCPTool(BaseMCPTool):
    """
    Gmail MCP Tool providing email management intelligence.
    Uses async httpx to interact with the Gmail REST API.
    """
    
    def __init__(self):
        self.base_url = "https://gmail.googleapis.com/gmail/v1/users/me"

    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="gmail.read_inbox",
                description="Read recent emails from the user's inbox.",
                parameters=[
                    ToolParameter(name="max_results", type="integer", description="Maximum number of emails to retrieve (default 10)", required=False)
                ]
            ),
            ToolDefinition(
                name="gmail.search_emails",
                description="Search emails based on a query string.",
                parameters=[
                    ToolParameter(name="query", type="string", description="The search query (e.g. 'from:boss@example.com')", required=True),
                    ToolParameter(name="max_results", type="integer", description="Maximum number of emails to retrieve", required=False)
                ]
            ),
            ToolDefinition(
                name="gmail.draft_reply",
                description="Create a draft reply to an existing email.",
                parameters=[
                    ToolParameter(name="thread_id", type="string", description="The ID of the thread to reply to.", required=True),
                    ToolParameter(name="to", type="string", description="The email address to reply to.", required=True),
                    ToolParameter(name="subject", type="string", description="The subject of the email.", required=True),
                    ToolParameter(name="body", type="string", description="The plaintext body of the draft.", required=True)
                ]
            ),
            ToolDefinition(
                name="gmail.send_email",
                description="Send a new email.",
                parameters=[
                    ToolParameter(name="to", type="string", description="The recipient email address.", required=True),
                    ToolParameter(name="subject", type="string", description="The subject of the email.", required=True),
                    ToolParameter(name="body", type="string", description="The plaintext body of the email.", required=True)
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
            if tool_name == "gmail.read_inbox":
                return await self._read_inbox(client, arguments.get("max_results", 10))
            elif tool_name == "gmail.search_emails":
                return await self._search_emails(client, arguments.get("query"), arguments.get("max_results", 10))
            elif tool_name == "gmail.draft_reply":
                return await self._draft_reply(
                    client, 
                    arguments.get("thread_id"), 
                    arguments.get("to"), 
                    arguments.get("subject"), 
                    arguments.get("body")
                )
            elif tool_name == "gmail.send_email":
                return await self._send_email(
                    client,
                    arguments.get("to"), 
                    arguments.get("subject"), 
                    arguments.get("body")
                )
            else:
                raise ValueError(f"Unknown Gmail tool: {tool_name}")

    async def _read_inbox(self, client: httpx.AsyncClient, max_results: int) -> Any:
        response = await client.get(f"{self.base_url}/messages", params={"q": "in:inbox", "maxResults": max_results})
        response.raise_for_status()
        return response.json()

    async def _search_emails(self, client: httpx.AsyncClient, query: str, max_results: int) -> Any:
        if not query:
            raise ValueError("query is required")
        response = await client.get(f"{self.base_url}/messages", params={"q": query, "maxResults": max_results})
        response.raise_for_status()
        return response.json()

    def _create_message(self, to: str, subject: str, body: str) -> str:
        """Create a base64url encoded email message string."""
        from email.message import EmailMessage
        msg = EmailMessage()
        msg.set_content(body)
        msg['To'] = to
        msg['Subject'] = subject
        
        # Base64url encode the message
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        return raw

    async def _draft_reply(self, client: httpx.AsyncClient, thread_id: str, to: str, subject: str, body: str) -> Any:
        if not all([thread_id, to, subject, body]):
            raise ValueError("thread_id, to, subject, and body are required")
            
        raw_message = self._create_message(to, subject, body)
        payload = {
            "message": {
                "raw": raw_message,
                "threadId": thread_id
            }
        }
        response = await client.post(f"{self.base_url}/drafts", json=payload)
        response.raise_for_status()
        return response.json()

    async def _send_email(self, client: httpx.AsyncClient, to: str, subject: str, body: str) -> Any:
        if not all([to, subject, body]):
            raise ValueError("to, subject, and body are required")
            
        raw_message = self._create_message(to, subject, body)
        payload = {
            "raw": raw_message
        }
        response = await client.post(f"{self.base_url}/messages/send", json=payload)
        response.raise_for_status()
        return response.json()

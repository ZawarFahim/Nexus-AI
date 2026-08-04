from typing import Dict, Any, List
from app.services.mcp.base_tool import BaseMCPTool
from app.schemas.mcp import ToolDefinition, ToolParameter
from app.models.user import User
from app.services.n8n_client import n8n_client
from app.schemas.n8n import N8nWebhookPayload

class N8nMCPTool(BaseMCPTool):
    """
    n8n MCP Tool.
    Acts as a bridge mapping specific AI actions directly to predefined n8n webhooks.
    """
    
    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="n8n.daily_briefing",
                description="Fetches today's events from Calendar, unread emails from Gmail, and open issues from GitHub by triggering an n8n workflow.",
                parameters=[]
            ),
            ToolDefinition(
                name="n8n.smart_email",
                description="Fetches unread emails, summarizes them, generates a draft reply, and waits for user confirmation before sending.",
                parameters=[]
            ),
            ToolDefinition(
                name="n8n.confirm_smart_email",
                description="Resumes the paused Smart Email workflow. Use this to approve or modify the draft reply.",
                parameters=[
                    ToolParameter(name="execution_id", type="string", description="The n8n execution ID of the paused workflow.", required=True),
                    ToolParameter(name="approved_reply", type="string", description="The finalized reply string to send.", required=True)
                ]
            )
        ]

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user: User) -> Any:
        if tool_name == "n8n.daily_briefing":
            payload = N8nWebhookPayload(
                webhook_id="daily-briefing",
                data={"user_id": str(user.id)}
            )
            result = await n8n_client.trigger_workflow(payload, user)
            if not result.success:
                raise RuntimeError(f"n8n Workflow Failed: {result.logs}")
            return result.data
            
        elif tool_name == "n8n.smart_email":
            payload = N8nWebhookPayload(
                webhook_id="smart-email",
                data={"user_id": str(user.id)}
            )
            result = await n8n_client.trigger_workflow(payload, user)
            if not result.success:
                raise RuntimeError(f"n8n Workflow Failed: {result.logs}")
            return result.data
            
        elif tool_name == "n8n.confirm_smart_email":
            payload = N8nWebhookPayload(
                webhook_id=f"confirm-email/{arguments.get('execution_id')}",
                data={"approved_reply": arguments.get("approved_reply")}
            )
            result = await n8n_client.trigger_workflow(payload, user)
            if not result.success:
                raise RuntimeError(f"n8n Workflow Failed: {result.logs}")
            return result.data
            
        else:
            raise ValueError(f"Unknown n8n tool: {tool_name}")

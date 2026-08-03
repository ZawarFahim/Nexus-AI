from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class N8nWebhookPayload(BaseModel):
    webhook_id: str = Field(..., description="The ID of the n8n webhook to trigger.")
    data: Dict[str, Any] = Field(default_factory=dict, description="The payload to send to the workflow.")

class N8nExecutionResult(BaseModel):
    success: bool = Field(..., description="Whether the workflow executed successfully.")
    data: Optional[Any] = Field(None, description="The parsed output from the Webhook Response node.")
    logs: Optional[str] = Field(None, description="Error logs or raw response text if parsing failed.")

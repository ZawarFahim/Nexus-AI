from pydantic import BaseModel, Field
from typing import List, Any, Dict, Optional

class CoordinatorRequest(BaseModel):
    prompt: str = Field(..., description="The natural language request from the user.")

class ExecutionLog(BaseModel):
    task: str = Field(..., description="The original task description.")
    tool_executed: Optional[str] = Field(None, description="The name of the MCP tool executed.")
    success: bool = Field(..., description="Whether the tool execution succeeded.")
    result: Optional[Any] = Field(None, description="The JSON result or error message from the tool.")

class CoordinatorResponse(BaseModel):
    final_response: str = Field(..., description="The final synthesized natural language response for the user.")
    execution_logs: List[ExecutionLog] = Field(default_factory=list, description="A log of all tasks executed to fulfill the request.")

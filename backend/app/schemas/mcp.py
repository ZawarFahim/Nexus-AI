from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ToolParameter(BaseModel):
    name: str = Field(..., description="The name of the parameter.")
    type: str = Field(..., description="The data type of the parameter (e.g., 'string', 'integer').")
    description: str = Field(..., description="A description of what the parameter does.")
    required: bool = Field(default=False, description="Whether this parameter is required.")

class ToolDefinition(BaseModel):
    name: str = Field(..., description="The unique name of the MCP tool.")
    description: str = Field(..., description="A detailed description of the tool's capabilities.")
    parameters: List[ToolParameter] = Field(default_factory=list, description="The required and optional parameters for this tool.")
    required_permissions: List[str] = Field(default_factory=list, description="Internal permission roles or scopes required to execute this tool.")

class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="The name of the tool to execute.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="The arguments to pass to the tool, mapping parameter names to values.")

class ToolExecuteResponse(BaseModel):
    success: bool = Field(..., description="Whether the tool execution succeeded.")
    result: Optional[Any] = Field(None, description="The structured or unstructured result of the execution.")
    error: Optional[str] = Field(None, description="An error message if the execution failed.")

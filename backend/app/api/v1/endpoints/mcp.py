from typing import List, Any
from fastapi import APIRouter, Depends, status
from app.api import deps
from app.schemas.mcp import ToolDefinition, ToolExecuteRequest, ToolExecuteResponse
from app.services.mcp_registry import mcp_registry
from app.models.user import User

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def mcp_health() -> Any:
    """Health endpoint for the MCP Layer."""
    return {
        "status": "ok", 
        "registered_tools_count": len(mcp_registry.get_all_tools())
    }

@router.get("/tools", response_model=List[ToolDefinition])
def get_tools(current_user: User = Depends(deps.get_current_user)) -> Any:
    """
    Discovery endpoint. Returns all registered MCP tools available for execution.
    Requires authentication.
    """
    return mcp_registry.get_all_tools()

@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Execute a specific MCP tool.
    Validates permissions, delegates to the registry, and returns the unified response.
    """
    # The registry handles lookup, permission validation, and safe execution
    response = await mcp_registry.execute_tool(request, current_user)
    
    if not response.success:
        # We could map specific errors to HTTP status codes, but for MCP, 
        # it is often better to return a 200 OK with the execution failure payload 
        # so the calling Agent can reason about the failure without crashing.
        pass
        
    return response

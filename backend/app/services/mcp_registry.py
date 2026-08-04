import logging
from typing import Dict, Any, Callable, Awaitable, List
from app.schemas.mcp import ToolDefinition, ToolExecuteRequest, ToolExecuteResponse, ToolParameter
from app.models.user import User

logger = logging.getLogger(__name__)

# Type alias for a tool handler callback
ToolHandler = Callable[[Dict[str, Any], User], Awaitable[Any]]

class MCPRegistry:
    """
    Model Context Protocol (MCP) Registry.
    Centralized hub for registering, discovering, and securely executing AI tools.
    """
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, ToolHandler] = {}
        self._register_internal_tools()

    def register_tool(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        """Register a new MCP tool with its execution callback."""
        if definition.name in self._tools:
            logger.warning(f"Tool {definition.name} is already registered. Overwriting.")
        
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler
        logger.info(f"Registered MCP tool: {definition.name}")

    def register_tool_instance(self, tool_instance) -> None:
        """Register a BaseMCPTool instance and all its definitions."""
        from app.services.mcp.base_tool import BaseMCPTool
        if not isinstance(tool_instance, BaseMCPTool):
            raise TypeError("tool_instance must inherit from BaseMCPTool")
            
        definitions = tool_instance.get_definitions()
        for definition in definitions:
            # We create a closure to capture the specific tool_name for the execute call
            async def handler(args: Dict[str, Any], user: User, t_name=definition.name) -> Any:
                return await tool_instance.execute(t_name, args, user)
                
            self.register_tool(definition, handler)

    def get_all_tools(self) -> List[ToolDefinition]:
        """Return all registered tools for agent discovery."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    async def execute_tool(self, request: ToolExecuteRequest, current_user: User) -> ToolExecuteResponse:
        """Execute a tool, handling basic permission checks and routing to the callback."""
        definition = self.get_tool(request.tool_name)
        handler = self._handlers.get(request.tool_name)

        if not definition or not handler:
            return ToolExecuteResponse(
                success=False,
                error=f"Tool '{request.tool_name}' not found in registry."
            )

        # Permission validation (mock logic for now: assume valid unless specific roles required)
        # In a real app, you would check current_user.roles against definition.required_permissions
        if definition.required_permissions:
            # Simple simulation: if any permissions are required, verify user is verified
            if not current_user.is_verified:
                 return ToolExecuteResponse(
                    success=False,
                    error=f"User lacks required permissions: {definition.required_permissions}"
                )

        try:
            # Execute the handler (e.g., triggering n8n webhook)
            result = await handler(request.arguments, current_user)
            return ToolExecuteResponse(
                success=True,
                result=result
            )
        except Exception as e:
            logger.error(f"Error executing tool {request.tool_name}: {e}")
            return ToolExecuteResponse(
                success=False,
                error=str(e)
            )

    def _register_internal_tools(self):
        """Register built-in tools for testing and basic functionality."""
        
        async def echo_handler(args: Dict[str, Any], user: User) -> Any:
            return {"echo": args.get("message", ""), "user": user.email}

        echo_def = ToolDefinition(
            name="system.echo",
            description="A test tool that echoes back the message.",
            parameters=[
                ToolParameter(name="message", type="string", description="Message to echo", required=True)
            ]
        )
        
        self.register_tool(echo_def, echo_handler)

        # Register GitHub Tool
        from app.services.mcp.github_tool import GitHubMCPTool
        github_tool = GitHubMCPTool()
        self.register_tool_instance(github_tool)
        
        # Register Gmail Tool
        from app.services.mcp.gmail_tool import GmailMCPTool
        gmail_tool = GmailMCPTool()
        self.register_tool_instance(gmail_tool)

        # Register n8n Tool
        from app.services.mcp.n8n_tool import N8nMCPTool
        n8n_tool = N8nMCPTool()
        self.register_tool_instance(n8n_tool)

        # Register Memory Tool
        from app.services.mcp.memory_tool import MemoryMCPTool
        memory_tool = MemoryMCPTool()
        self.register_tool_instance(memory_tool)

        # Register Browser Tool
        from app.services.mcp.browser_tool import BrowserMCPTool
        browser_tool = BrowserMCPTool()
        self.register_tool_instance(browser_tool)

        # Register Calendar Tool
        from app.services.mcp.calendar_tool import CalendarMCPTool
        calendar_tool = CalendarMCPTool()
        self.register_tool_instance(calendar_tool)

# Singleton registry instance
mcp_registry = MCPRegistry()

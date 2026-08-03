from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.schemas.mcp import ToolDefinition
from app.models.user import User

class BaseMCPTool(ABC):
    """
    Abstract Base Class for all MCP Tools.
    Enforces a standard interface for tool definition and execution routing.
    """

    @abstractmethod
    def get_definitions(self) -> List[ToolDefinition]:
        """
        Return a list of ToolDefinitions that this tool provides.
        Usually a single class might provide multiple related MCP tools (e.g. github.list_repos, github.summary).
        """
        pass

    @abstractmethod
    async def execute(self, tool_name: str, arguments: Dict[str, Any], user: User) -> Any:
        """
        Execute the tool based on the provided tool_name and arguments.
        """
        pass

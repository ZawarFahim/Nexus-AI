from typing import Dict, Any, List
from app.services.mcp.base_tool import BaseMCPTool
from app.schemas.mcp import ToolDefinition, ToolParameter
from app.models.user import User
from app.services.memory_service import memory_service
from app.schemas.memory import MemoryCreate, MemorySearchRequest

class MemoryMCPTool(BaseMCPTool):
    """
    Memory MCP Tool.
    Allows AI agents to autonomously save to and search the user's Long-Term Memory.
    """
    
    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="memory.save",
                description="Save important facts, preferences, or notes into the user's long-term memory for future retrieval.",
                parameters=[
                    ToolParameter(name="content", type="string", description="The core content/fact to remember.", required=True),
                    ToolParameter(name="category", type="string", description="A short category tag (e.g., 'preference', 'work', 'personal').", required=False),
                    ToolParameter(name="title", type="string", description="A brief 3-5 word title for the memory.", required=False)
                ]
            ),
            ToolDefinition(
                name="memory.search",
                description="Perform a semantic search across the user's long-term memory to retrieve previously learned facts or context.",
                parameters=[
                    ToolParameter(name="query", type="string", description="The natural language query to search for.", required=True),
                    ToolParameter(name="limit", type="integer", description="Max number of results to return (default 5).", required=False),
                    ToolParameter(name="category", type="string", description="Filter by a specific category.", required=False)
                ]
            ),
            ToolDefinition(
                name="memory.search_files",
                description="Perform a semantic search across the user's uploaded files (PDFs, Markdown, etc) to retrieve relevant text chunks.",
                parameters=[
                    ToolParameter(name="query", type="string", description="The natural language query to search for.", required=True),
                    ToolParameter(name="limit", type="integer", description="Max number of chunks to return (default 5).", required=False)
                ]
            )
        ]

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user: User) -> Any:
        if tool_name == "memory.save":
            create_req = MemoryCreate(
                content=arguments.get("content"),
                category=arguments.get("category", "General"),
                title=arguments.get("title")
            )
            result = await memory_service.save_memory(user, create_req)
            return {
                "success": True,
                "message": "Memory saved successfully.",
                "importance_score": result.importance_score,
                "memory_id": str(result.id)
            }
            
        elif tool_name == "memory.search":
            search_req = MemorySearchRequest(
                query=arguments.get("query"),
                limit=arguments.get("limit", 5),
                category=arguments.get("category")
            )
            results = await memory_service.search_memory(user, search_req)
            
            return {
                "success": True,
                "count": len(results),
                "memories": [
                    {
                        "title": m.title,
                        "content": m.content,
                        "category": m.category,
                        "importance_score": m.importance_score,
                        "created_at": str(m.created_at)
                    } for m in results
                ]
            }
            
        elif tool_name == "memory.search_files":
            from app.services.rag_service import rag_service
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            
            results = await rag_service.search(query, limit=limit)
            return {
                "success": True,
                "count": len(results),
                "chunks": [
                    {
                        "score": r["score"],
                        "document_id": r["payload"].get("document_id"),
                        "title": r["payload"].get("title"),
                        "text": r["payload"].get("text")
                    } for r in results
                ]
            }
            
        else:
            raise ValueError(f"Unknown memory tool: {tool_name}")

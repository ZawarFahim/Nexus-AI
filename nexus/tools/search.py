import urllib.request
import urllib.parse
import json
import logging
import re
from typing import Any
from nexus.core.protocols import ToolResult
from nexus.tools.registry import Tool

logger = logging.getLogger(__name__)

def web_search(query: str) -> str:
    """Perform a web search using the Wikipedia API for real-time information retrieval."""
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&utf8=&format=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Nexus-AI/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            results = data.get('query', {}).get('search', [])
            if not results:
                return "No results found."
            
            # Extract top 3 results
            snippets = []
            for item in results[:3]:
                # Basic HTML tag stripping
                snippet = re.sub('<[^<]+>', '', item['snippet'])
                snippets.append(f"Title: {item['title']}\nSummary: {snippet}")
            return "\n\n".join(snippets)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Error performing web search: {str(e)}"

def web_search_tool() -> Tool:
    def execute(arguments: dict[str, Any]) -> ToolResult:
        query = arguments.get("query", "")
        if not query:
            return ToolResult("Error: Search query cannot be empty.")
            
        results = web_search(query)
        return ToolResult(f"Web Search Results for '{query}':\n{results}")

    return Tool(
        name="web_search",
        description="Search the web (Wikipedia) to find real-time information about people, places, concepts, or recent events. Always use this when the user asks a question about facts you are unsure about.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The specific topic or question to search for."
                }
            },
            "required": ["query"]
        },
        run=execute,
    )

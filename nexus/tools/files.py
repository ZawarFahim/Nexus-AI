"""Tool for managing files and folders on the Windows filesystem."""

import os
import json
import logging
from pathlib import Path
from typing import Any, Final

from nexus.core.protocols import ToolResult
from nexus.tools.registry import Tool

logger = logging.getLogger(__name__)

NAME: Final = "manage_files"

DESCRIPTION: Final = (
    "Smart File Assistant: use this to find, inspect, open, organize, rename, move, and create files/folders. "
    "Use this for any request related to the user's filesystem. "
    "If the target file is ambiguous, use search first to find its path. "
    "If an action requires high permissions (like deleting files), "
    "you MUST first ask the user for confirmation and pass 'confirmed: true'."
)

PARAMETERS: Final = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": [
                "search",
                "open",
                "create_folder",
                "rename",
                "move",
                "copy",
                "delete"
            ],
            "description": "The filesystem operation to perform."
        },
        "query": {
            "type": "string",
            "description": "Search query for filenames (e.g., 'latest PDF'). Required for search."
        },
        "target_path": {
            "type": "string",
            "description": "Absolute path to the target file or folder for operations."
        },
        "destination_path": {
            "type": "string",
            "description": "Absolute path for the destination (for move, copy, rename, create_folder)."
        },
        "confirmed": {
            "type": "boolean",
            "description": "Set to true ONLY if you explicitly asked the user for permission in a previous turn."
        }
    },
    "required": ["operation"]
}

def _search(query: str | None) -> list[dict[str, Any]]:
    """Basic search implementation for Commit 1."""
    if not query:
        return []
        
    query_lower = query.lower()
    results = []
    
    # Just search Documents for now as a basic foundation
    docs_dir = Path.home() / "Documents"
    
    try:
        if docs_dir.exists():
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    if query_lower in file.lower():
                        full_path = Path(root) / file
                        try:
                            stat = full_path.stat()
                            results.append({
                                "name": file,
                                "path": str(full_path),
                                "size_bytes": stat.st_size,
                            })
                        except OSError:
                            pass
                        
                        if len(results) >= 20: # Limit for basic version
                            break
                if len(results) >= 20:
                    break
    except Exception as e:
        logger.error(f"[Files] Basic search error: {e}")
        
    return results

def _run(arguments: dict[str, Any]) -> ToolResult:
    operation = arguments.get("operation")
    confirmed = arguments.get("confirmed", False)
    
    logger.info(f"[Files] Running operation: {operation}")
    
    result_data = {
        "success": False,
        "operation": operation
    }
    
    try:
        if operation == "search":
            query = arguments.get("query", "")
            result_data["query"] = query
            results = _search(query)
            result_data["results"] = results
            result_data["success"] = True
        else:
            result_data["error"] = f"Operation '{operation}' is not fully implemented yet."
            
    except Exception as e:
        logger.exception(f"[Files] Operation {operation} failed")
        result_data["error"] = str(e)
        
    return ToolResult(json.dumps(result_data))

def files_tool() -> Tool:
    """The smart file assistant capability, ready to register."""
    return Tool(name=NAME, description=DESCRIPTION, parameters=PARAMETERS, run=_run)

"""Tool for managing files and folders on the Windows filesystem."""

import os
import json
import shutil
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

def _verify_path_safe(path_str: str) -> Path:
    """Normalize and validate path."""
    p = Path(path_str).resolve()
    if not p.is_absolute():
        raise ValueError("Paths must be absolute.")
    return p

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
            
        elif operation == "open":
            target = _verify_path_safe(arguments.get("target_path", ""))
            if not target.exists():
                raise FileNotFoundError(f"File not found: {target}")
            os.startfile(str(target))
            result_data["success"] = True
            result_data["message"] = f"Opened {target.name}"
            
        elif operation == "create_folder":
            target = _verify_path_safe(arguments.get("target_path", ""))
            if target.exists():
                result_data["success"] = True
                result_data["message"] = f"Folder already exists: {target}"
            else:
                target.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    result_data["success"] = True
                    result_data["message"] = f"Created folder: {target}"
                else:
                    raise RuntimeError("Verification failed: folder was not created.")
                    
        elif operation in ("move", "copy", "rename"):
            target = _verify_path_safe(arguments.get("target_path", ""))
            dest = _verify_path_safe(arguments.get("destination_path", ""))
            
            if not target.exists():
                raise FileNotFoundError(f"Source not found: {target}")
                
            if dest.exists() and operation == "rename":
                raise FileExistsError(f"Destination already exists: {dest}")
                
            if operation == "copy":
                shutil.copy2(target, dest)
                final_dest = dest if dest.is_file() else dest / target.name
                if final_dest.exists():
                    result_data["success"] = True
                    result_data["message"] = f"Copied {target.name} to {dest}"
                else:
                    raise RuntimeError("Verification failed: copy did not complete.")
                    
            elif operation in ("move", "rename"):
                shutil.move(str(target), str(dest))
                final_dest = dest if dest.is_file() else dest / target.name
                if final_dest.exists() and not target.exists():
                    result_data["success"] = True
                    result_data["message"] = f"Moved/Renamed {target.name} to {dest}"
                else:
                    raise RuntimeError("Verification failed: move/rename did not complete properly.")
        else:
            result_data["error"] = f"Operation '{operation}' is not fully implemented yet."
            
    except Exception as e:
        logger.exception(f"[Files] Operation {operation} failed")
        result_data["error"] = str(e)
        
    return ToolResult(json.dumps(result_data))

def files_tool() -> Tool:
    """The smart file assistant capability, ready to register."""
    return Tool(name=NAME, description=DESCRIPTION, parameters=PARAMETERS, run=_run)

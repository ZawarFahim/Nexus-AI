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
        "extensions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of extensions to filter (e.g. ['.pdf', '.txt']). Use to find 'Python files', 'documents'."
        },
        "min_size_bytes": {
            "type": "integer",
            "description": "Optional minimum file size."
        },
        "max_size_bytes": {
            "type": "integer",
            "description": "Optional maximum file size."
        },
        "modified_after": {
            "type": "number",
            "description": "Optional timestamp (epoch). Use to find 'files modified today/yesterday'."
        },
        "sort_by": {
            "type": "string",
            "enum": ["relevance", "size_desc", "size_asc", "modified_desc", "modified_asc"],
            "description": "How to sort results. E.g. 'size_desc' for 'largest files', 'modified_desc' for 'latest/recent files'."
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

def _search(
    query: str | None,
    extensions: list[str] | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    modified_after: float | None = None,
    sort_by: str | None = None
) -> list[dict[str, Any]]:
    """Smart search implementation for Commit 3."""
    query_lower = query.lower() if query else ""
    results = []
    
    roots = [
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
        Path.home() / "Pictures",
        Path.home() / "Videos",
    ]
    
    for root_dir in roots:
        if not root_dir.exists(): continue
        
        try:
            for root, dirs, files in os.walk(root_dir):
                # Don't recurse too deep
                if len(Path(root).parts) > len(root_dir.parts) + 3:
                    dirs[:] = []
                    continue
                    
                for file in files:
                    # Filters
                    if query_lower and query_lower not in file.lower():
                        continue
                    if extensions and not any(file.lower().endswith(ext.lower()) for ext in extensions):
                        continue
                        
                    full_path = Path(root) / file
                    try:
                        stat = full_path.stat()
                        
                        if min_size is not None and stat.st_size < min_size:
                            continue
                        if max_size is not None and stat.st_size > max_size:
                            continue
                        if modified_after is not None and stat.st_mtime < modified_after:
                            continue
                            
                        # Basic score based on exact match vs partial match
                        score = 1.0
                        if query_lower and query_lower == file.lower():
                            score = 2.0
                            
                        results.append({
                            "name": file,
                            "path": str(full_path),
                            "size_bytes": stat.st_size,
                            "modified": stat.st_mtime,
                            "score": score
                        })
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"[Files] Basic search error in {root_dir}: {e}")
            
    # Sorting
    if sort_by == "size_desc":
        results.sort(key=lambda x: x["size_bytes"], reverse=True)
    elif sort_by == "size_asc":
        results.sort(key=lambda x: x["size_bytes"])
    elif sort_by == "modified_desc":
        results.sort(key=lambda x: x["modified"], reverse=True)
    elif sort_by == "modified_asc":
        results.sort(key=lambda x: x["modified"])
    else:
        results.sort(key=lambda x: x["score"], reverse=True)
        
    return results[:30] # Limit results

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
            exts = arguments.get("extensions")
            min_s = arguments.get("min_size_bytes")
            max_s = arguments.get("max_size_bytes")
            mod_a = arguments.get("modified_after")
            srt = arguments.get("sort_by")
            
            result_data["query"] = query
            results = _search(
                query=query, 
                extensions=exts, 
                min_size=min_s, 
                max_size=max_s, 
                modified_after=mod_a, 
                sort_by=srt
            )
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

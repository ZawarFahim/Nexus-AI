"""Tool for controlling the Windows desktop and installed applications."""

import time
import logging
from typing import Any, Final, List, Dict

from nexus.core.protocols import ToolResult
from nexus.tools.registry import Tool
from nexus.tools import automation

logger = logging.getLogger(__name__)

NAME: Final = "control_desktop"

DESCRIPTION: Final = (
    "Control the user's desktop, launch applications, and automate GUI interactions. "
    "Call this to open apps (e.g., Spotify, Chrome, VS Code), type text, click elements, or simulate hotkeys. "
    "You can chain multiple actions together in a single call. "
    "If an action requires high permissions (like executing raw shell commands or deleting files), "
    "you MUST first ask the user for confirmation and pass 'confirmed: true'."
)

PARAMETERS: Final = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "description": "Sequential list of desktop automation actions.",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": [
                            "launch_application",
                            "focus_window",
                            "type_text",
                            "click_element",
                            "hotkey",
                            "verify_state",
                            "execute_shell"
                        ],
                        "description": "The type of action to perform."
                    },
                    "target": {
                        "type": "string",
                        "description": "Target app name, window title, or element description."
                    },
                    "value": {
                        "type": "string",
                        "description": "Optional value, like text to type or shell command to run."
                    }
                },
                "required": ["action_type", "target"]
            }
        },
        "confirmed": {
            "type": "boolean",
            "description": "Set to true ONLY if you explicitly asked the user for permission in a previous turn."
        }
    },
    "required": ["actions"]
}

HIGH_RISK_ACTIONS = {"execute_shell"}

def _run(arguments: dict[str, Any]) -> ToolResult:
    actions = arguments.get("actions", [])
    confirmed = arguments.get("confirmed", False)
    
    if not actions:
        return ToolResult("No actions specified.")
        
    results = []
    
    for idx, action in enumerate(actions):
        action_type = action.get("action_type")
        target = action.get("target")
        value = action.get("value")
        
        logger.info(f"[Desktop] Executing action {idx+1}/{len(actions)}: {action_type} on '{target}'")
        
        # Permission check
        if action_type in HIGH_RISK_ACTIONS and not confirmed:
            return ToolResult(
                f"Action '{action_type}' is HIGH RISK. You must ask the user for confirmation out loud, "
                "and only retry with 'confirmed: true' if they explicitly agree."
            )
            
        started = time.perf_counter()
        res = {"action": action_type, "target": target}
        
        try:
            if action_type == "launch_application":
                step_res = automation.launch_application(target)
            elif action_type == "focus_window":
                step_res = automation.focus_window(target)
            elif action_type == "type_text":
                step_res = automation.type_text(value or target, target if value else None)
            elif action_type == "click_element":
                # Wait briefly for UI to settle
                time.sleep(0.5)
                step_res = automation.click_element(target, value) # value could be window keyword
            elif action_type == "hotkey":
                step_res = automation.send_hotkey(value or target, target if value else None)
            elif action_type == "verify_state":
                # For verify_state, just check if window exists for now
                step_res = automation.focus_window(target)
            elif action_type == "execute_shell":
                import subprocess
                subprocess.Popen(value, shell=True)
                step_res = {"success": True, "message": "Command launched."}
            else:
                step_res = {"success": False, "error": f"Unknown action: {action_type}"}
                
        except Exception as e:
            step_res = {"success": False, "error": str(e)}
            
        res.update(step_res)
        res["duration_ms"] = int((time.perf_counter() - started) * 1000)
        results.append(res)
        
        if not step_res.get("success", False):
            logger.warning(f"[Desktop] Action failed: {step_res.get('error')}")
            import json
            return ToolResult(
                f"Desktop automation failed at step {idx+1} ({action_type}). "
                f"Error: {step_res.get('error')}. "
                "Consider using the 'look_at_screen' tool to visually inspect what went wrong if needed.\n"
                f"Results: {json.dumps(results)}"
            )
            
        time.sleep(0.2) # Small delay between generic actions
        
    import json
    return ToolResult(
        f"Desktop automation completed successfully.\nResults: {json.dumps(results)}"
    )

def desktop_tool() -> Tool:
    """The generic desktop control capability, ready to register."""
    return Tool(name=NAME, description=DESCRIPTION, parameters=PARAMETERS, run=_run)

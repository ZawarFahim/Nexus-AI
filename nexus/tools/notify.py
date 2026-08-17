import logging
import subprocess
from typing import Any
from nexus.core.protocols import ToolResult
from nexus.tools.registry import Tool

logger = logging.getLogger(__name__)

def send_windows_notification(title: str, message: str) -> bool:
    """Send a native Windows balloon tip notification using PowerShell."""
    try:
        # We use PowerShell's built-in forms assembly to send a native balloon tip
        # without requiring any pip packages like win10toast or plyer.
        ps_script = f"""
        [reflection.assembly]::loadwithpartialname("System.Windows.Forms") | Out-Null
        [reflection.assembly]::loadwithpartialname("System.Drawing") | Out-Null
        $notify = new-object system.windows.forms.notifyicon
        $notify.icon = [System.Drawing.SystemIcons]::Information
        $notify.visible = $true
        $notify.showballoontip(10, "{title}", "{message}", [system.windows.forms.tooltipicon]::None)
        Start-Sleep -Seconds 3
        $notify.Dispose()
        """
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], 
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False

def notify_tool() -> Tool:
    def execute(arguments: dict[str, Any]) -> ToolResult:
        title = arguments.get("title", "Nexus")
        message = arguments.get("message", "")
        
        if not message:
            return ToolResult("Error: Notification message cannot be empty.")
            
        success = send_windows_notification(title, message)
        if success:
            return ToolResult(f"Sent native Windows notification: '{title} - {message}'")
        else:
            return ToolResult("Failed to send notification.")

    return Tool(
        name="send_notification",
        description="Sends a native Windows desktop notification popup to the user. Use this to alert the user of something important if they are not actively looking at the chat.",
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the notification (default: Nexus)."
                },
                "message": {
                    "type": "string",
                    "description": "The main text body of the notification."
                }
            },
            "required": ["message"]
        },
        run=execute,
    )

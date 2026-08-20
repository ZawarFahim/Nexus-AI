import logging
from datetime import datetime
import psutil

from nexus.tools.registry import Tool

logger = logging.getLogger(__name__)

def morning_briefing_tool() -> Tool:
    """Provides a morning briefing tool."""
    
    def handler() -> str:
        logger.info("Executing Morning Briefing...")
        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:\\').percent
            sys_health = f"CPU: {cpu}%, RAM: {ram}%, Disk: {disk}%"
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            sys_health = "System health check failed."
            
        briefing = f"Current Date & Time: {now}\nSystem Health: {sys_health}\n"
        briefing += "Please summarize this information into a friendly, spoken morning briefing for the user."
        
        return briefing

    return Tool(
        name="morning_briefing",
        description="Generates a comprehensive morning briefing including date, time, and system health.",
        parameters={},
        handler=handler
    )

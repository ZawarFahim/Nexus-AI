import logging
from datetime import datetime
import psutil
import urllib.request
import xml.etree.ElementTree as ET

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
            
        try:
            weather = "Could not fetch weather."
            req = urllib.request.Request("https://wttr.in/?format=3", headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                weather = response.read().decode('utf-8').strip()
        except Exception as e:
            logger.error(f"Failed to get weather: {e}")

        try:
            headlines = []
            req = urllib.request.Request("http://feeds.bbci.co.uk/news/rss.xml", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                for item in root.findall('./channel/item')[:3]:
                    headlines.append(item.find('title').text)
            news = "\\n- ".join(headlines)
        except Exception as e:
            logger.error(f"Failed to get news: {e}")
            news = "Could not fetch top news."

        briefing = f"Current Date & Time: {now}\\nSystem Health: {sys_health}\\nWeather: {weather}\\nTop News:\\n- {news}\\n"
        briefing += "Please summarize this information into a friendly, spoken morning briefing for the user. Do not read the URLs, just the headlines."
        
        return briefing

    return Tool(
        name="morning_briefing",
        description="Generates a comprehensive morning briefing including date, time, and system health.",
        parameters={},
        handler=handler
    )

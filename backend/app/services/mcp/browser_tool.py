import logging
import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.services.mcp.base_tool import BaseMCPTool
from app.schemas.mcp import ToolDefinition, ToolParameter
from app.models.user import User

logger = logging.getLogger(__name__)

class BrowserMCPTool(BaseMCPTool):
    """
    Browser MCP Tool.
    Grants the AI the ability to open a headless browser, navigate pages, fill forms,
    and extract data using Playwright. Maintains state per user.
    """
    
    def __init__(self):
        super().__init__()
        # State management for active browser sessions keyed by user_id
        self._contexts: Dict[str, Dict[str, Any]] = {}
        self._playwright = None
        self._browser: Optional[Browser] = None
        # Use a background task to initialize the playwright engine
        asyncio.create_task(self._init_browser())

    async def _init_browser(self):
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            logger.info("Playwright browser initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")

    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="browser.open",
                description="Launch a new browser session for the user. Must be called before navigating.",
                parameters=[]
            ),
            ToolDefinition(
                name="browser.navigate",
                description="Navigate the active browser session to a specified URL.",
                parameters=[
                    ToolParameter(name="url", type="string", description="The full URL to navigate to.", required=True)
                ]
            ),
            ToolDefinition(
                name="browser.fill",
                description="Fill an input field on the current page.",
                parameters=[
                    ToolParameter(name="selector", type="string", description="The CSS selector for the input field.", required=True),
                    ToolParameter(name="value", type="string", description="The text to fill into the input field.", required=True)
                ]
            ),
            ToolDefinition(
                name="browser.extract",
                description="Extract the text content of a specific element on the page.",
                parameters=[
                    ToolParameter(name="selector", type="string", description="The CSS selector to extract text from (e.g. 'body' or '.content').", required=True)
                ]
            ),
            ToolDefinition(
                name="browser.screenshot",
                description="Take a base64 encoded screenshot of the current page view.",
                parameters=[]
            ),
            ToolDefinition(
                name="browser.close",
                description="Close the user's active browser session to free up memory.",
                parameters=[]
            )
        ]

    async def _get_user_page(self, user_id: str) -> Page:
        state = self._contexts.get(user_id)
        if not state or not state.get("page"):
            raise ValueError("No active browser session. Call 'browser.open' first.")
        return state["page"]

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user: User) -> Any:
        user_id = str(user.id)
        
        # Ensure base browser is ready
        if not self._browser:
            await self._init_browser()
            if not self._browser:
                return {"success": False, "error": "Browser engine failed to start."}

        try:
            if tool_name == "browser.open":
                if user_id in self._contexts:
                    await self.execute("browser.close", {}, user)
                    
                context: BrowserContext = await self._browser.new_context(
                    viewport={'width': 1280, 'height': 800}
                )
                page: Page = await context.new_page()
                self._contexts[user_id] = {"context": context, "page": page}
                return {"success": True, "message": "Browser session opened successfully."}
                
            elif tool_name == "browser.navigate":
                page = await self._get_user_page(user_id)
                url = arguments.get("url")
                # Aggressive timeout to prevent hanging
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title = await page.title()
                return {"success": True, "message": f"Navigated to {url}", "title": title}
                
            elif tool_name == "browser.fill":
                page = await self._get_user_page(user_id)
                selector = arguments.get("selector")
                value = arguments.get("value")
                await page.fill(selector, value, timeout=10000)
                return {"success": True, "message": f"Filled selector '{selector}'"}
                
            elif tool_name == "browser.extract":
                page = await self._get_user_page(user_id)
                selector = arguments.get("selector")
                content = await page.inner_text(selector, timeout=10000)
                # Truncate extremely long content to prevent LLM context overflow
                if len(content) > 10000:
                    content = content[:10000] + "... [TRUNCATED]"
                return {"success": True, "content": content}
                
            elif tool_name == "browser.screenshot":
                page = await self._get_user_page(user_id)
                screenshot_bytes = await page.screenshot(type="jpeg", quality=50, timeout=10000)
                import base64
                encoded = base64.b64encode(screenshot_bytes).decode('utf-8')
                return {"success": True, "base64_image": encoded}
                
            elif tool_name == "browser.close":
                state = self._contexts.get(user_id)
                if state:
                    await state["context"].close()
                    del self._contexts[user_id]
                return {"success": True, "message": "Browser session closed securely."}
                
            else:
                raise ValueError(f"Unknown browser tool action: {tool_name}")
                
        except Exception as e:
            logger.error(f"Browser action '{tool_name}' failed for user {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    def __del__(self):
        """Cleanup playwright resources if the process shuts down."""
        if self._playwright:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._playwright.stop())
            except Exception:
                pass

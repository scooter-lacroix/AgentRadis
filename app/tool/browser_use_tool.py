import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from app.tool.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

class BrowserUseTool(BaseTool):
    """Tool for browser automation using Playwright."""
    
    name: str = "browser_use"
    description: str = "Interact with a web browser to perform various actions"
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "get_title", "get_text", "screenshot"],
                "description": "The action to perform"
            },
            "url": {
                "type": "string",
                "description": "URL for navigation"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self):
        super().__init__()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()
        
    async def _ensure_browser(self):
        """Ensure browser is initialized."""
        try:
            async with self._lock:
                if not self._playwright:
                    logger.info("Starting Playwright")
                    self._playwright = await async_playwright().start()
                    
                if not self._browser:
                    logger.info("Launching browser")
                    self._browser = await self._playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-setuid-sandbox',
                            '--dns-prefetch-disable=false'
                        ]
                    )
                    
                if not self._context:
                    logger.info("Creating browser context")
                    self._context = await self._browser.new_context(
                        ignore_https_errors=True
                    )
                    
                if not self._page:
                    logger.info("Creating new page")
                    self._page = await self._context.new_page()
                    
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            await self.cleanup()
            raise
            
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters."""
        try:
            result = await self.run(**kwargs)
            if result["status"] == "success":
                return ToolResult(output=result)
            else:
                return ToolResult(error=result["error"])
        except Exception as e:
            logger.error(f"Error executing browser action: {str(e)}")
            return ToolResult(error=str(e))
            
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute browser action."""
        try:
            await self._ensure_browser()  # This already uses the lock
            action = kwargs.get("action")
            logger.info(f"Executing browser action: {action}")
            
            if action == "navigate":
                url = kwargs.get("url", "about:blank")
                logger.info(f"Navigating to URL: {url}")
                await self._page.goto(url)
                title = await self._page.title()
                return {"status": "success", "title": title}
                
            elif action == "get_title":
                title = await self._page.title()
                return {"status": "success", "title": title}
                
            elif action == "get_text":
                text = await self._page.text_content("body")
                return {"status": "success", "text": text}
                
            elif action == "screenshot":
                screenshot = await self._page.screenshot()
                return {"status": "success", "screenshot": screenshot}
                
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Error executing browser action: {str(e)}")
            await self.cleanup()
            return {"status": "error", "error": str(e)}
                
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self._page:
                logger.info("Closing page")
                await self._page.close()
                self._page = None
                
            if self._context:
                logger.info("Closing browser context")
                await self._context.close()
                self._context = None
                
            if self._browser:
                logger.info("Closing browser")
                await self._browser.close()
                self._browser = None
                
            if self._playwright:
                logger.info("Stopping Playwright")
                await self._playwright.stop()
                self._playwright = None
                
        except Exception as e:
            logger.error(f"Error cleaning up browser resources: {str(e)}")
            raise

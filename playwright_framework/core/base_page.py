"""Base Page: shared, auto-waiting interaction primitives for every Page Object."""
from __future__ import annotations

from playwright.sync_api import Locator, Page

from utils.logger import get_logger

logger = get_logger(__name__)


class BasePage:
    """Common navigation and interaction helpers all page objects inherit."""

    def __init__(self, page: Page, base_url: str, timeout_ms: int = 10_000) -> None:
        self.page = page
        self.base_url = base_url
        self.timeout_ms = timeout_ms

    def navigate(self, path: str = "") -> None:
        """Navigate to base_url + path, waiting for the load event."""
        url = f"{self.base_url}{path}"
        logger.info("Navigating to %s", url)
        self.page.goto(url, timeout=self.timeout_ms)

    def click(self, locator: Locator) -> None:
        locator.wait_for(state="visible", timeout=self.timeout_ms)
        locator.click()

    def fill(self, locator: Locator, text: str) -> None:
        locator.wait_for(state="visible", timeout=self.timeout_ms)
        locator.fill(text)

    def get_text(self, locator: Locator) -> str:
        locator.wait_for(state="visible", timeout=self.timeout_ms)
        return locator.inner_text()

    def is_visible(self, locator: Locator, timeout_ms: int | None = None) -> bool:
        """Return True if locator becomes visible within timeout, else False."""
        try:
            locator.wait_for(state="visible", timeout=timeout_ms or self.timeout_ms)
            return True
        except Exception:
            return False

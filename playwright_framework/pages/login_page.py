"""Page Object for the FleetLocate login page."""
from __future__ import annotations

from playwright.sync_api import Page

from core.base_page import BasePage
from utils.logger import get_logger

logger = get_logger(__name__)


class LoginPage(BasePage):
    """Encapsulates locators and actions for the FleetLocate v5 /signin page.

    Note: the form also carries a hidden `input[name='email']` honeypot field
    (server-rendered but never shown) — the real username field is `#userid`.
    Do not fill the honeypot; bots that do are typically rejected/flagged.
    """

    LOGIN_PATH = "/signin?q=1"

    def __init__(self, page: Page, base_url: str, timeout_ms: int = 10_000) -> None:
        super().__init__(page, base_url, timeout_ms)
        self.userid_input = page.locator("#userid")
        self.password_input = page.locator("input[name='password']")
        self.sign_in_button = page.locator("#submitButton")

    def open(self) -> "LoginPage":
        self.navigate(self.LOGIN_PATH)
        return self

    def enter_email(self, email: str) -> "LoginPage":
        self.fill(self.userid_input, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        self.fill(self.password_input, password)
        return self

    def click_sign_in(self) -> "LoginPage":
        self.click(self.sign_in_button)
        return self

    def login(self, email: str, password: str) -> None:
        """Fill credentials and submit in one call."""
        logger.info("Attempting login as %s", email)
        self.enter_email(email).enter_password(password).click_sign_in()

    def is_displayed(self) -> bool:
        """True if the login form (userid + password fields) is visible."""
        return self.is_visible(self.userid_input) and self.is_visible(self.password_input)

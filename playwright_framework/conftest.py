"""Shared Pytest fixtures: config and page-object factories."""
import pytest

from config.settings import Settings, get_settings
from pages.login_page import LoginPage


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture
def login_page(page, settings: Settings) -> LoginPage:
    """A ready-to-use LoginPage bound to this test's browser page."""
    return LoginPage(page, settings.base_url, settings.default_timeout_ms)

"""Smoke test for the login flow, using the LoginPage POM."""
import pytest

from utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.smoke
def test_valid_login_leaves_login_page(login_page, settings):
    assert settings.test_email and settings.test_password, (
        "TEST_EMAIL / TEST_PASSWORD must be set (see .env.example)"
    )

    login_page.open()
    assert login_page.is_displayed(), "Login form did not render"

    login_page.login(settings.test_email, settings.test_password)

    login_page.page.wait_for_url(
        lambda url: "/signin" not in url,
        timeout=settings.default_timeout_ms,
        wait_until="commit",
    )
    assert "/signin" not in login_page.page.url


@pytest.mark.smoke
def test_login_returns_page_title(login_page, settings):
    assert settings.test_email and settings.test_password, (
        "TEST_EMAIL / TEST_PASSWORD must be set (see .env.example)"
    )

    login_page.open()
    login_page.login(settings.test_email, settings.test_password)
    login_page.page.wait_for_url(
        lambda url: "/signin" not in url,
        timeout=settings.default_timeout_ms,
        wait_until="commit",
    )
    login_page.page.wait_for_load_state("domcontentloaded")

    title = login_page.page.title()
    logger.info("Post-login page title: %s", title)
    print(f"PAGE_TITLE={title}")

    assert title

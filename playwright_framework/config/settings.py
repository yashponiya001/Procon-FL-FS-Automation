"""Centralized, environment-driven configuration for the framework."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration for a test session."""

    base_url: str
    headless: bool
    default_timeout_ms: int
    test_email: str
    test_password: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build (and cache) Settings from environment variables / .env."""
    return Settings(
        base_url=os.getenv("BASE_URL", "https://fleetv5.fleetlocate.com.au"),
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        default_timeout_ms=int(os.getenv("DEFAULT_TIMEOUT_MS", "10000")),
        test_email=os.getenv("TEST_EMAIL", ""),
        test_password=os.getenv("TEST_PASSWORD", ""),
    )

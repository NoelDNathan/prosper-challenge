"""
This module contains the fixtures for the tests.
"""
from pathlib import Path
import os

import pytest
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load the environment variables."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _ensure_credentials():
    """Ensure the Healthie credentials are configured."""
    email = os.environ.get("HEALTHIE_EMAIL")
    password = os.environ.get("HEALTHIE_PASSWORD")
    if not email or not password:
        pytest.skip("Healthie credentials not configured; skipping live test.")
    
    return email, password


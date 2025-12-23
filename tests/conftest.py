"""Pytest configuration and shared fixtures."""
import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Generate a valid Fernet key for testing
from cryptography.fernet import Fernet
_test_key = Fernet.generate_key().decode()

# Set test environment variables before importing app
os.environ["ENCRYPTION_KEY"] = _test_key
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DEPLOYMENT_TYPE"] = "local"
os.environ["LOG_LEVEL"] = "ERROR"

from app.main import app
from shared.database import Database, get_database
from shared.models.base import Base


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create a fresh test database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sample_unifi_config():
    """Sample UniFi controller configuration."""
    return {
        "controller_url": "https://192.168.1.1:8443",
        "username": "admin",
        "password": "test-password",
        "site_id": "default",
        "verify_ssl": False,
    }


@pytest.fixture
def sample_device_data():
    """Sample Wi-Fi client device data from UniFi API."""
    return {
        "mac": "aa:bb:cc:dd:ee:ff",
        "name": "Test Device",
        "ip": "192.168.1.100",
        "ap_mac": "11:22:33:44:55:66",
        "signal": -45,
        "essid": "HomeNetwork",
    }

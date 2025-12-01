"""
Configuration management for UniFi Toolkit
"""
from pydantic_settings import BaseSettings
from typing import Optional


class ToolkitSettings(BaseSettings):
    """
    UniFi Toolkit settings loaded from environment variables
    """
    # Required
    encryption_key: str

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/unifi_toolkit.db"

    # Logging
    log_level: str = "INFO"

    # UniFi Controller (optional - can be configured via UI)
    unifi_controller_url: Optional[str] = None
    unifi_username: Optional[str] = None
    unifi_password: Optional[str] = None
    unifi_api_key: Optional[str] = None
    unifi_site_id: str = "default"
    unifi_verify_ssl: bool = False

    # Tool-specific settings
    stalker_refresh_interval: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


_settings: Optional[ToolkitSettings] = None


def get_settings() -> ToolkitSettings:
    """
    Get the global settings instance (singleton pattern)
    """
    global _settings
    if _settings is None:
        _settings = ToolkitSettings()
    return _settings

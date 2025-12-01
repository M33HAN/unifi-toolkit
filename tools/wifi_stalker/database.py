"""
Database models for Wi-Fi Stalker
"""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from shared.models.base import Base


class TrackedDevice(Base):
    """
    Represents a Wi-Fi device that the user wants to track
    """
    __tablename__ = "stalker_tracked_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mac_address = Column(String, unique=True, nullable=False, index=True)
    friendly_name = Column(String, nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = Column(DateTime, nullable=True)
    current_ap_mac = Column(String, nullable=True)
    current_ap_name = Column(String, nullable=True)
    current_ip_address = Column(String, nullable=True)
    current_signal_strength = Column(Integer, nullable=True)
    is_connected = Column(Boolean, default=False, nullable=False)
    site_id = Column(String, nullable=False)

    # Relationship to connection history
    history = relationship("ConnectionHistory", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TrackedDevice(mac={self.mac_address}, name={self.friendly_name}, connected={self.is_connected})>"


class ConnectionHistory(Base):
    """
    Tracks roaming events - when devices connect/disconnect or move between APs
    """
    __tablename__ = "stalker_connection_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("stalker_tracked_devices.id"), nullable=False, index=True)
    ap_mac = Column(String, nullable=True)
    ap_name = Column(String, nullable=True)
    connected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    disconnected_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    signal_strength = Column(Integer, nullable=True)

    # Relationship to device
    device = relationship("TrackedDevice", back_populates="history")

    def __repr__(self):
        return f"<ConnectionHistory(device_id={self.device_id}, ap={self.ap_name}, connected={self.connected_at})>"


class WebhookConfig(Base):
    """
    Stores webhook configurations for sending device event notifications
    Supports Slack, Discord, and generic/n8n webhooks
    """
    __tablename__ = "stalker_webhook_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    webhook_type = Column(String, nullable=False)  # 'slack', 'discord', 'n8n'
    url = Column(String, nullable=False)

    # Event triggers
    event_device_connected = Column(Boolean, default=True, nullable=False)
    event_device_disconnected = Column(Boolean, default=True, nullable=False)
    event_device_roamed = Column(Boolean, default=True, nullable=False)

    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_triggered = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<WebhookConfig(name={self.name}, type={self.webhook_type}, enabled={self.enabled})>"

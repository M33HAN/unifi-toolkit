"""
Webhook delivery system for sending device event notifications
"""
import aiohttp
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


async def deliver_webhook(
    webhook_url: str,
    webhook_type: str,
    event_type: str,
    device_name: str,
    device_mac: str,
    ap_name: Optional[str] = None,
    signal_strength: Optional[int] = None
):
    """
    Deliver a webhook notification

    Args:
        webhook_url: The webhook URL to send to
        webhook_type: Type of webhook ('slack', 'discord', 'n8n')
        event_type: Type of event ('connected', 'disconnected', 'roamed')
        device_name: Friendly name of the device
        device_mac: MAC address of the device
        ap_name: Name of the AP (for connected/roamed events)
        signal_strength: Signal strength in dBm (for connected/roamed events)
    """
    try:
        # Format message based on webhook type
        if webhook_type == 'slack':
            payload = format_slack_message(event_type, device_name, device_mac, ap_name, signal_strength)
        elif webhook_type == 'discord':
            payload = format_discord_message(event_type, device_name, device_mac, ap_name, signal_strength)
        elif webhook_type == 'n8n':
            payload = format_generic_message(event_type, device_name, device_mac, ap_name, signal_strength)
        else:
            logger.error(f"Unknown webhook type: {webhook_type}")
            return False

        # Send webhook
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, timeout=10) as response:
                if response.status in [200, 204]:
                    logger.info(f"Webhook delivered successfully to {webhook_type}: {event_type} for {device_name}")
                    return True
                else:
                    logger.error(f"Webhook delivery failed: {response.status} - {await response.text()}")
                    return False

    except Exception as e:
        logger.error(f"Error delivering webhook: {e}", exc_info=True)
        return False


def format_slack_message(
    event_type: str,
    device_name: str,
    device_mac: str,
    ap_name: Optional[str],
    signal_strength: Optional[int]
) -> dict:
    """
    Format a message for Slack webhook

    Args:
        event_type: Type of event ('connected', 'disconnected', 'roamed')
        device_name: Friendly name of the device
        device_mac: MAC address of the device
        ap_name: Name of the AP
        signal_strength: Signal strength in dBm

    Returns:
        Dictionary with Slack message payload
    """
    # Determine emoji and color based on event type
    if event_type == 'connected':
        emoji = ':white_check_mark:'
        color = 'good'
        title = f"{device_name} Connected"
        text = f"Device connected to {ap_name}"
    elif event_type == 'disconnected':
        emoji = ':x:'
        color = 'danger'
        title = f"{device_name} Disconnected"
        text = "Device went offline"
    else:  # roamed
        emoji = ':arrows_counterclockwise:'
        color = '#2196F3'
        title = f"{device_name} Roamed"
        text = f"Device moved to {ap_name}"

    # Build fields
    fields = [
        {
            "title": "Device",
            "value": device_name,
            "short": True
        },
        {
            "title": "MAC Address",
            "value": device_mac,
            "short": True
        }
    ]

    if ap_name and event_type != 'disconnected':
        fields.append({
            "title": "Access Point",
            "value": ap_name,
            "short": True
        })

    if signal_strength is not None and event_type != 'disconnected':
        fields.append({
            "title": "Signal",
            "value": f"{signal_strength} dBm",
            "short": True
        })

    return {
        "attachments": [
            {
                "color": color,
                "title": f"{emoji} {title}",
                "text": text,
                "fields": fields,
                "footer": "Wi-Fi Stalker | UniFi Toolkit",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }
        ]
    }


def format_discord_message(
    event_type: str,
    device_name: str,
    device_mac: str,
    ap_name: Optional[str],
    signal_strength: Optional[int]
) -> dict:
    """
    Format a message for Discord webhook

    Args:
        event_type: Type of event ('connected', 'disconnected', 'roamed')
        device_name: Friendly name of the device
        device_mac: MAC address of the device
        ap_name: Name of the AP
        signal_strength: Signal strength in dBm

    Returns:
        Dictionary with Discord message payload
    """
    # Determine color and description based on event type
    if event_type == 'connected':
        color = 0x4CAF50  # Green
        title = "✅ Device Connected"
        description = f"**{device_name}** connected to {ap_name}"
    elif event_type == 'disconnected':
        color = 0xF44336  # Red
        title = "❌ Device Disconnected"
        description = f"**{device_name}** went offline"
    else:  # roamed
        color = 0x2196F3  # Blue
        title = "🔄 Device Roamed"
        description = f"**{device_name}** moved to {ap_name}"

    # Build fields
    fields = [
        {
            "name": "MAC Address",
            "value": device_mac,
            "inline": True
        }
    ]

    if ap_name and event_type != 'disconnected':
        fields.append({
            "name": "Access Point",
            "value": ap_name,
            "inline": True
        })

    if signal_strength is not None and event_type != 'disconnected':
        fields.append({
            "name": "Signal Strength",
            "value": f"{signal_strength} dBm",
            "inline": True
        })

    return {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "footer": {
                    "text": "Wi-Fi Stalker | UniFi Toolkit"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }


def format_generic_message(
    event_type: str,
    device_name: str,
    device_mac: str,
    ap_name: Optional[str],
    signal_strength: Optional[int]
) -> dict:
    """
    Format a message for generic/n8n webhook

    Args:
        event_type: Type of event ('connected', 'disconnected', 'roamed')
        device_name: Friendly name of the device
        device_mac: MAC address of the device
        ap_name: Name of the AP
        signal_strength: Signal strength in dBm

    Returns:
        Dictionary with generic JSON payload
    """
    return {
        "event_type": event_type,
        "device": {
            "name": device_name,
            "mac_address": device_mac
        },
        "access_point": ap_name,
        "signal_strength": signal_strength,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "unifi-toolkit"
    }

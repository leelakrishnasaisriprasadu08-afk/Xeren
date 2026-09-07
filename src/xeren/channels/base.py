"""BaseChannel — Abstract gateway for messaging platforms (Telegram, Discord, WhatsApp)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"


@dataclass
class ChannelMessage:
    channel: ChannelType
    sender_id: str
    text: str
    chat_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseChannel(ABC):
    """Unified interface for external messaging bots."""

    def __init__(self, channel_type: ChannelType, config: Optional[Dict[str, Any]] = None) -> None:
        self.channel_type = channel_type
        self.config = config or {}
        self.is_connected: bool = False

    @abstractmethod
    def send_message(self, chat_id: str, text: str) -> bool:
        """Send a message to a recipient or group chat."""
        pass

    @abstractmethod
    def handle_incoming_message(self, message: ChannelMessage) -> str:
        """Handle incoming command or user inquiry."""
        pass


__all__ = ["BaseChannel", "ChannelType", "ChannelMessage"]

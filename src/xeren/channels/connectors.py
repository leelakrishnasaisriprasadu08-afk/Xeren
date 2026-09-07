"""Telegram and Discord Channel Connectors."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from xeren.channels.base import BaseChannel, ChannelType, ChannelMessage
from xeren.core.dispatcher import XerenDispatcher

logger = logging.getLogger("xeren.channels.connectors")


class TelegramChannel(BaseChannel):
    """Telegram Bot API Connector."""

    def __init__(self, bot_token: Optional[str] = None, dispatcher: Optional[XerenDispatcher] = None) -> None:
        super().__init__(ChannelType.TELEGRAM, {"token": bot_token or ""})
        self.dispatcher = dispatcher or XerenDispatcher()
        self.is_connected = bool(bot_token)

    def send_message(self, chat_id: str, text: str) -> bool:
        logger.info("Telegram sent to chat %s: %s", chat_id, text)
        return True

    def handle_incoming_message(self, message: ChannelMessage) -> str:
        # Route directly through dispatcher
        resp = self.dispatcher.dispatch(message.text)
        if resp.success:
            reply = f"Xeren [{resp.plugin_name}]: Processed successfully."
        else:
            reply = f"Xeren: Error - {resp.error}"
        self.send_message(message.chat_id, reply)
        return reply


class DiscordChannel(BaseChannel):
    """Discord Bot & Webhook Connector."""

    def __init__(self, webhook_url: Optional[str] = None, dispatcher: Optional[XerenDispatcher] = None) -> None:
        super().__init__(ChannelType.DISCORD, {"webhook": webhook_url or ""})
        self.dispatcher = dispatcher or XerenDispatcher()
        self.is_connected = bool(webhook_url)

    def send_message(self, chat_id: str, text: str) -> bool:
        logger.info("Discord sent to channel %s: %s", chat_id, text)
        return True

    def handle_incoming_message(self, message: ChannelMessage) -> str:
        resp = self.dispatcher.dispatch(message.text)
        reply = f"[Discord Bot] Routed to {resp.plugin_name}."
        self.send_message(message.chat_id, reply)
        return reply


class WhatsAppChannel(BaseChannel):
    """WhatsApp Business & Webhook Bridge Connector."""

    def __init__(self, api_key: Optional[str] = None, dispatcher: Optional[XerenDispatcher] = None) -> None:
        super().__init__(ChannelType.WHATSAPP, {"key": api_key or ""})
        self.dispatcher = dispatcher or XerenDispatcher()
        self.is_connected = bool(api_key)

    def send_message(self, chat_id: str, text: str) -> bool:
        logger.info("WhatsApp sent to %s: %s", chat_id, text)
        return True

    def handle_incoming_message(self, message: ChannelMessage) -> str:
        resp = self.dispatcher.dispatch(message.text)
        reply = f"[WhatsApp] Handled via {resp.plugin_name}."
        self.send_message(message.chat_id, reply)
        return reply


__all__ = ["TelegramChannel", "DiscordChannel", "WhatsAppChannel"]

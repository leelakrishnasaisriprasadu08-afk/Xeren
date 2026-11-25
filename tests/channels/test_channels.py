"""Unit tests for multi-channel chatbot gateways (Telegram, Discord, WhatsApp)."""

from __future__ import annotations

import pytest

from xeren.channels.base import ChannelType, ChannelMessage
from xeren.channels.connectors import TelegramChannel, DiscordChannel, WhatsAppChannel
from xeren.channels.manager import ChannelsManager


class TestChannels:
    def test_telegram_incoming_message_flow(self):
        channel = TelegramChannel(bot_token="test_token_123")
        msg = ChannelMessage(
            channel=ChannelType.TELEGRAM,
            sender_id="tg_user_42",
            text="deep search about quantum cryptography",
            chat_id="chat_999",
        )
        reply = channel.handle_incoming_message(msg)
        assert "research" in reply or "Processed successfully" in reply

    def test_discord_broadcast(self):
        manager = ChannelsManager()
        results = manager.broadcast_alert("New Fiverr order #9821 incoming!")
        assert results["discord"] is True
        assert results["telegram"] is True
        assert results["whatsapp"] is True

"""ChannelsManager — Manages external messaging connections."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from xeren.channels.base import BaseChannel, ChannelType, ChannelMessage
from xeren.channels.connectors import TelegramChannel, DiscordChannel, WhatsAppChannel
from xeren.core.vault import UserVault

logger = logging.getLogger("xeren.channels.manager")


class ChannelsManager:
    """Orchestrates all chatbot connectors and routes external messages."""

    def __init__(self, vault: Optional[UserVault] = None) -> None:
        self.vault = vault or UserVault()
        self.channels: Dict[ChannelType, BaseChannel] = {
            ChannelType.TELEGRAM: TelegramChannel(),
            ChannelType.DISCORD: DiscordChannel(),
            ChannelType.WHATSAPP: WhatsAppChannel(),
        }

    def get_channel(self, channel_type: ChannelType) -> BaseChannel:
        return self.channels[channel_type]

    def broadcast_alert(self, text: str, target_channels: Optional[List[ChannelType]] = None) -> Dict[str, bool]:
        """Broadcast status or urgent order alert across connected channels."""
        targets = target_channels or list(self.channels.keys())
        results = {}
        for chan_type in targets:
            chan = self.channels[chan_type]
            results[chan_type.value] = chan.send_message("broadcast_channel", text)
        return results


__all__ = ["ChannelsManager"]

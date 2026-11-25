"""Xeren Swarm Registry.

Central catalog and directory holding the definitions and execution handlers
for all micro-bots in the system.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from xeren.swarm.micro_bots import (
    BaseMicroBot,
    BotAppLauncher,
    BotAuditLogger,
    BotCitationBuilder,
    BotCredentialSanitizer,
    BotDestructiveGuard,
    BotDirectoryScanner,
    BotFactVerifier,
    BotFastAPIRouter,
    BotFilePatcher,
    BotMemoryFence,
    BotPageCleaner,
    BotPathJail,
    BotReactBuilder,
    BotSearchExpander,
    BotSQLOptimizer,
    BotSummarizer,
    BotSyntaxLinter,
    BotSystemDiagnostic,
    BotTailwindStyler,
    BotTerminalRunner,
)

logger = logging.getLogger("xeren.swarm.registry")


class SwarmRegistry:
    """Registry managing discovery, indexing, and lookup of micro-bots."""

    def __init__(self) -> None:
        self._bots: Dict[str, BaseMicroBot] = {}
        self._load_foundational_swarm()

    def _load_foundational_swarm(self) -> None:
        """Register the first 20 core micro-bots across the 4 clusters."""
        bots: List[BaseMicroBot] = [
            # Coding Cluster
            BotReactBuilder(),
            BotTailwindStyler(),
            BotFastAPIRouter(),
            BotSQLOptimizer(),
            BotSyntaxLinter(),
            # Research Cluster
            BotSearchExpander(),
            BotPageCleaner(),
            BotSummarizer(),
            BotFactVerifier(),
            BotCitationBuilder(),
            # OS & Local Filesystem Cluster
            BotFilePatcher(),
            BotDirectoryScanner(),
            BotAppLauncher(),
            BotTerminalRunner(),
            BotSystemDiagnostic(),
            # Security & Privacy Cluster
            BotDestructiveGuard(),
            BotCredentialSanitizer(),
            BotMemoryFence(),
            BotPathJail(),
            BotAuditLogger(),
        ]
        for b in bots:
            self.register(b)

    def register(self, bot: BaseMicroBot) -> None:
        """Add a micro-bot to the registry."""
        self._bots[bot.bot_id] = bot
        logger.debug("Registered micro-bot: %s (%s)", bot.bot_id, bot.cluster)

    def get(self, bot_id: str) -> Optional[BaseMicroBot]:
        """Retrieve a micro-bot by its unique ID."""
        return self._bots.get(bot_id)

    def list_all(self) -> List[BaseMicroBot]:
        """Return all registered micro-bots."""
        return list(self._bots.values())

    def list_by_cluster(self, cluster: str) -> List[BaseMicroBot]:
        """Return all micro-bots matching a specific cluster."""
        return [b for b in self._bots.values() if b.cluster.lower() == cluster.lower()]

    def count(self) -> int:
        """Total number of registered micro-bots."""
        return len(self._bots)

    def find_best_bot(self, task_description: str) -> Optional[BaseMicroBot]:
        """Deterministically match the best micro-bot for a given task description."""
        clean = task_description.lower()

        # Coding matches
        if any(w in clean for w in ["react", "jsx", "tsx", "component"]):
            return self.get("Bot-101-ReactBuilder")
        if any(w in clean for w in ["tailwind", "css", "style", "glass"]):
            return self.get("Bot-102-TailwindStyler")
        if any(w in clean for w in ["fastapi", "route", "endpoint", "api"]):
            return self.get("Bot-103-FastAPIRouter")
        if any(w in clean for w in ["sql", "database", "table", "query"]):
            return self.get("Bot-104-SQLOptimizer")
        if any(w in clean for w in ["lint", "syntax", "ast", "verify code"]):
            return self.get("Bot-105-SyntaxLinter")

        # Research matches
        if any(w in clean for w in ["search query", "keyword", "search angle"]):
            return self.get("Bot-201-SearchExpander")
        if any(w in clean for w in ["clean page", "scrape url", "fetch page"]):
            return self.get("Bot-202-PageCleaner")
        if any(w in clean for w in ["summarize", "summary", "bullets"]):
            return self.get("Bot-203-Summarizer")
        if any(w in clean for w in ["verify claim", "fact check", "truth"]):
            return self.get("Bot-204-FactVerifier")
        if any(w in clean for w in ["citation", "reference"]):
            return self.get("Bot-205-CitationBuilder")

        # OS matches
        if any(w in clean for w in ["patch", "replace in file", "edit file"]):
            return self.get("Bot-301-FilePatcher")
        if any(w in clean for w in ["list directory", "scan files", "show files"]):
            return self.get("Bot-302-DirectoryScanner")
        if any(w in clean for w in ["launch app", "open app"]):
            return self.get("Bot-303-AppLauncher")
        if any(w in clean for w in ["run command", "terminal", "powershell", "bash"]):
            return self.get("Bot-304-TerminalRunner")
        if any(w in clean for w in ["system stats", "cpu", "specs", "ram"]):
            return self.get("Bot-305-SystemDiagnostic")

        # Security matches
        if any(w in clean for w in ["destructive", "dangerous", "delete check"]):
            return self.get("Bot-401-DestructiveGuard")
        if any(w in clean for w in ["sanitize", "redact", "secret", "key"]):
            return self.get("Bot-402-CredentialSanitizer")

        return None


# Global singleton
default_swarm_registry = SwarmRegistry()

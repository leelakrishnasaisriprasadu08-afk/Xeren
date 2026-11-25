"""Xeren Micro-Bot Swarm & Hybrid Fallback Architecture."""

from xeren.swarm.micro_bots import BaseMicroBot, MicroBotResult
from xeren.swarm.registry import SwarmRegistry, default_swarm_registry
from xeren.swarm.fallback_gateway import (
    HybridFallbackGateway,
    default_fallback_gateway,
    CapabilityAssessment,
    FallbackResult,
)

__all__ = [
    "BaseMicroBot",
    "MicroBotResult",
    "SwarmRegistry",
    "default_swarm_registry",
    "HybridFallbackGateway",
    "default_fallback_gateway",
    "CapabilityAssessment",
    "FallbackResult",
]

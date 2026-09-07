"""Verification and Experience plugin adapters for Xeren Autonomous Work Agent."""

from xeren.agent.plugins.experience import (
    ExperienceInput,
    ExperienceOutput,
    ExperiencePlugin,
)
from xeren.agent.plugins.verification import (
    VerificationInput,
    VerificationOutput,
    VerificationPlugin,
)

__all__ = [
    "VerificationInput",
    "VerificationOutput",
    "VerificationPlugin",
    "ExperienceInput",
    "ExperienceOutput",
    "ExperiencePlugin",
]

"""Xeren Coding Plugin.

Autonomous code generation, syntax validation, static analysis, sandbox execution,
testing, and multi-stage verification.
"""

from xeren.plugins.coding.manifest import CODING_PLUGIN_MANIFEST
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.coding.registry import CodingToolRegistry
from xeren.plugins.coding.schemas import (
    CodeAnalysisReport,
    CodingInput,
    CodingOperation,
    CodingResult,
    Diagnostic,
    DiagnosticSeverity,
    ExecutionConfig,
    ExecutionOutput,
    FileArtifact,
    TestCaseResult,
    TestStatus,
    TestSummary,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.coding.tools.execution import (
    BaseCodeExecutor,
    SecurityViolationError,
    SubprocessSandboxExecutor,
)
from xeren.plugins.coding.workflow import CodingWorkflow

__all__ = [
    "CodingPlugin",
    "CODING_PLUGIN_MANIFEST",
    "CodingInput",
    "CodingResult",
    "CodingOperation",
    "CodingWorkflow",
    "CodingToolRegistry",
    "FileArtifact",
    "ExecutionConfig",
    "ExecutionOutput",
    "TestSummary",
    "TestCaseResult",
    "TestStatus",
    "Diagnostic",
    "DiagnosticSeverity",
    "VerificationResult",
    "VerificationStatus",
    "CodeAnalysisReport",
    "BaseCodeExecutor",
    "SubprocessSandboxExecutor",
    "SecurityViolationError",
]

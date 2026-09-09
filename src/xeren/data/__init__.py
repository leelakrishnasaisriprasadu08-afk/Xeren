"""Experience and training data management for Xeren agent learning."""

from xeren.data.dataset import (
    ExperienceDataset,
    load_jsonl_dataset,
    save_jsonl_dataset,
)
from xeren.data.formatter import (
    ChatMessage,
    DPOExample,
    ExperienceFormatter,
    SFTChatExample,
    StructuredAgentExample,
)
from xeren.data.pipeline import (
    PipelineManifest,
    TrainingDataPipeline,
)
from xeren.data.schema import (
    ActionStep,
    AlternativeCandidate,
    DatasetSplit,
    ExperienceRecord,
    RetrievalItem,
    ReviewStatus,
    VerificationDetails,
)
from xeren.data.validator import DatasetValidator, ValidationResult

__all__ = [
    # Schema
    "ActionStep",
    "AlternativeCandidate",
    "DatasetSplit",
    "ExperienceRecord",
    "RetrievalItem",
    "ReviewStatus",
    "VerificationDetails",
    # Validator
    "DatasetValidator",
    "ValidationResult",
    # Dataset
    "ExperienceDataset",
    "load_jsonl_dataset",
    "save_jsonl_dataset",
    # Formatter
    "ChatMessage",
    "SFTChatExample",
    "StructuredAgentExample",
    "DPOExample",
    "ExperienceFormatter",
    # Pipeline
    "PipelineManifest",
    "TrainingDataPipeline",
]

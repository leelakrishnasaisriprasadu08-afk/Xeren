"""Configuration parameters for Xeren agent model training."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Hyperparameters and runtime settings for Xeren agent training."""

    model_name_or_path: str = Field(
        default="xeren-agent-base",
        description="Base open-weight model name or local path (e.g. Qwen/Qwen2.5-Coder-7B)",
    )
    output_dir: str = Field(
        default="checkpoints/xeren-agent",
        description="Output directory for model weights and checkpoints",
    )
    epochs: int = Field(
        default=3,
        ge=1,
        description="Total training epochs",
    )
    batch_size: int = Field(
        default=4,
        ge=1,
        description="Per-device batch size",
    )
    gradient_accumulation_steps: int = Field(
        default=4,
        ge=1,
        description="Number of update steps to accumulate before backward/update pass",
    )
    learning_rate: float = Field(
        default=2e-5,
        gt=0.0,
        description="Peak learning rate for AdamW optimizer",
    )
    weight_decay: float = Field(
        default=0.01,
        ge=0.0,
        description="L2 weight decay penalty",
    )
    warmup_ratio: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Ratio of total steps for linear learning rate warmup",
    )
    max_seq_length: int = Field(
        default=2048,
        ge=16,
        description="Maximum sequence length in tokens",
    )
    seed: int = Field(
        default=42,
        description="Random seed for reproducibility",
    )
    device: str = Field(
        default="auto",
        description="Target compute device: 'auto', 'cuda', or 'cpu'",
    )
    fp16: bool = Field(
        default=False,
        description="Whether to use FP16 half-precision",
    )
    bf16: bool = Field(
        default=False,
        description="Whether to use BF16 bfloat16 precision",
    )
    eval_steps: int = Field(
        default=100,
        ge=1,
        description="Evaluation interval in training steps",
    )
    save_steps: int = Field(
        default=200,
        ge=1,
        description="Checkpoint save interval in training steps",
    )
    logging_steps: int = Field(
        default=10,
        ge=1,
        description="Logging interval in training steps",
    )
    save_total_limit: int = Field(
        default=3,
        ge=1,
        description="Maximum number of historical checkpoints to retain",
    )
    mask_prompt_labels: bool = Field(
        default=True,
        description="Mask prompt / user tokens with -100 to compute loss exclusively on agent generation",
    )

    @property
    def effective_batch_size(self) -> int:
        """Calculate effective batch size across gradient accumulation steps."""
        return self.batch_size * self.gradient_accumulation_steps

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()

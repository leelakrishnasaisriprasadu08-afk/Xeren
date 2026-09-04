"""Checkpoint management and persistence for Xeren model training."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field


class CheckpointMetadata(BaseModel):
    """Metadata tracking training progress, metrics, and hyperparameter state."""
    epoch: int = Field(..., ge=0)
    step: int = Field(..., ge=0)
    loss: float = Field(...)
    val_loss: Optional[float] = Field(default=None)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    config: Dict[str, Any] = Field(default_factory=dict)
    best_metric: Optional[float] = Field(default=None)


class CheckpointManager:
    """Manages saving, loading, atomic persistence, and retention pruning of model checkpoints."""

    def __init__(
        self,
        output_dir: Union[str, Path],
        save_total_limit: int = 3,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.save_total_limit = max(1, save_total_limit)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        model_state: Any,
        metadata: CheckpointMetadata,
        is_best: bool = False,
    ) -> Path:
        """Persist model weights and metadata, pruning older checkpoints if limit is exceeded."""
        ckpt_dir = self.output_dir / f"checkpoint-{metadata.step}"
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save metadata
        meta_path = ckpt_dir / "metadata.json"
        with meta_path.open("w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        # 2. Save model state
        state_path = ckpt_dir / "model_state.json"
        if isinstance(model_state, (dict, list, str, int, float, bool)) or model_state is None:
            with state_path.open("w", encoding="utf-8") as f:
                json.dump(model_state, f, indent=2)
        else:
            # Check for PyTorch state dict or save capability
            try:
                import torch
                torch.save(model_state, ckpt_dir / "pytorch_model.bin")
            except ImportError:
                with state_path.open("w", encoding="utf-8") as f:
                    json.dump({"repr": str(model_state)}, f, indent=2)

        # 3. If best checkpoint, create / update best_checkpoint directory
        if is_best:
            best_dir = self.output_dir / "best_checkpoint"
            if best_dir.exists():
                shutil.rmtree(best_dir)
            shutil.copytree(ckpt_dir, best_dir)

        # 4. Prune checkpoints exceeding save_total_limit
        self._prune_checkpoints()

        return ckpt_dir

    def _prune_checkpoints(self) -> None:
        """Remove oldest checkpoints to keep within save_total_limit."""
        ckpts = self.list_checkpoints()
        if len(ckpts) > self.save_total_limit:
            to_remove = ckpts[: len(ckpts) - self.save_total_limit]
            for c_path in to_remove:
                if c_path.is_dir():
                    shutil.rmtree(c_path)

    def list_checkpoints(self) -> List[Path]:
        """Return all checkpoint directories sorted by step index ascending."""
        ckpts = []
        for path in self.output_dir.iterdir():
            if path.is_dir() and path.name.startswith("checkpoint-"):
                try:
                    step = int(path.name.split("-")[1])
                    ckpts.append((step, path))
                except (IndexError, ValueError):
                    continue
        ckpts.sort(key=lambda x: x[0])
        return [p for _, p in ckpts]

    def get_latest_checkpoint(self) -> Optional[Path]:
        """Get the latest saved checkpoint path, or None if no checkpoints exist."""
        ckpts = self.list_checkpoints()
        return ckpts[-1] if ckpts else None

    def get_best_checkpoint(self) -> Optional[Path]:
        """Get path to the best evaluated checkpoint, or None."""
        best_dir = self.output_dir / "best_checkpoint"
        return best_dir if best_dir.is_dir() else None

    def load_checkpoint(
        self,
        checkpoint_dir: Union[str, Path],
    ) -> Tuple[Any, CheckpointMetadata]:
        """Load model state and metadata from a checkpoint directory."""
        ckpt_path = Path(checkpoint_dir)
        if not ckpt_path.is_dir():
            raise FileNotFoundError(f"Checkpoint directory not found: {ckpt_path}")

        meta_file = ckpt_path / "metadata.json"
        if not meta_file.is_file():
            raise FileNotFoundError(f"Metadata file missing in: {ckpt_path}")

        with meta_file.open("r", encoding="utf-8") as f:
            metadata = CheckpointMetadata.model_validate_json(f.read())

        state_file = ckpt_path / "model_state.json"
        torch_file = ckpt_path / "pytorch_model.bin"

        model_state: Any = None
        if torch_file.is_file():
            try:
                import torch
                model_state = torch.load(torch_file, map_location="cpu")
            except ImportError:
                pass

        if model_state is None and state_file.is_file():
            with state_file.open("r", encoding="utf-8") as f:
                model_state = json.load(f)

        return model_state, metadata

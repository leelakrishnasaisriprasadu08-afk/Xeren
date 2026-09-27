"""
Xeren MoS — Specialist Runner
===============================
Executes individual SpecialistTasks by loading the specialist's checkpoint
and running inference.

Currently supports two modes:
  1. STUB mode — used when specialist checkpoint is not yet trained.
     Returns a structured placeholder so the dispatch pipeline can be
     tested end-to-end before all 12 models are trained.
  2. NATIVE mode — loads the actual Xeren checkpoint and runs inference.

When you train a specialist (M1, M2, ... M12), just drop the checkpoint
into its registered path and the runner auto-upgrades to NATIVE mode.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from .protocol import SpecialistResult, SpecialistTask, TaskStatus
from .specialist_registry import SpecialistID, SpecialistRegistry

logger = logging.getLogger("xeren.mos.specialist_runner")


class SpecialistRunner:
    """
    Runs a SpecialistTask using the best available backend:
      - NATIVE  : actual trained specialist checkpoint
      - FALLBACK: main Xeren model with specialist-focused prompt
      - STUB    : placeholder output for untrained specialists
    """

    def __init__(self, main_llm=None, tokenizer=None):
        """
        Args:
            main_llm: Optional reference to the main Xeren LLM client.
                      Used as fallback when a specialist checkpoint is not yet trained.
            tokenizer: Optional reference to XerenTokenizer. Auto-loaded if None.
        """
        self._main_llm = main_llm
        self._tokenizer = tokenizer
        self._loaded_specialists: dict = {}  # specialist_id -> loaded model

    def _has_checkpoint(self, path) -> bool:
        """Check if path is a .pt file or directory containing a .pt checkpoint."""
        p = Path(path)
        if not p.exists():
            return False
        if p.is_file() and p.suffix == ".pt":
            return True
        if p.is_dir():
            return any(p.glob("*.pt"))
        return False

    async def run(self, task: SpecialistTask) -> SpecialistResult:
        """Execute a SpecialistTask and return the result."""
        t_start = time.monotonic()
        spec = self._get_spec(task.specialist_id)

        try:
            # Try native checkpoint first
            if spec and self._has_checkpoint(spec.checkpoint_path):
                output = await self._run_native(task, spec)
                mode = "NATIVE"
            # Fallback to main model with specialist prompt
            elif self._main_llm:
                output = await self._run_with_main_model(task)
                mode = "FALLBACK"
            # Stub — no model available yet
            else:
                output = self._run_stub(task)
                mode = "STUB"

            execution_ms = (time.monotonic() - t_start) * 1000
            logger.debug("[Runner] %s (%s) completed in %.1fms", task.specialist_name, mode, execution_ms)

            return SpecialistResult(
                task_trace_id=task.trace_id,
                specialist_id=task.specialist_id,
                status=TaskStatus.SUCCESS,
                output=output,
                confidence=1.0 if mode == "NATIVE" else 0.7 if mode == "FALLBACK" else 0.3,
                execution_ms=execution_ms,
            )

        except Exception as e:
            logger.error("[Runner] %s failed: %s", task.specialist_name, e, exc_info=True)
            execution_ms = (time.monotonic() - t_start) * 1000
            return SpecialistResult(
                task_trace_id=task.trace_id,
                specialist_id=task.specialist_id,
                status=TaskStatus.FAILED,
                output="",
                error=str(e),
                confidence=0.0,
                execution_ms=execution_ms,
            )

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------

    async def _run_native(self, task: SpecialistTask, spec) -> str:
        """Run inference on the specialist's own trained checkpoint."""
        from training.src.model.checkpoint_utils import load_native_xeren_model, generate_text
        from training.src.tokenizer.train_tokenizer import XerenTokenizer

        sid = task.specialist_id
        if sid not in self._loaded_specialists:
            if self._tokenizer is None:
                tok_path = Path("training/checkpoints/tokenizer_32k")
                self._tokenizer = XerenTokenizer.load(str(tok_path))
            model, cfg = load_native_xeren_model(spec.checkpoint_path, self._tokenizer.vocab_size)
            self._loaded_specialists[sid] = model

        model = self._loaded_specialists[sid]
        prompt = (
            f"<|system|>\nYou are the {task.specialist_name} specialist within the Xeren AI system. "
            f"Role: {self._get_role_description(task.specialist_id)}.\n"
            f"<|user|>\n{task.sub_task}\n"
            f"<|assistant|>\n"
        )
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: generate_text(
                model,
                self._tokenizer,
                prompt,
                max_new_tokens=task.max_tokens or 128,
            ),
        )
        return output

    async def _run_with_main_model(self, task: SpecialistTask) -> str:
        """Use the main Xeren model to answer, but with a specialist-focused system prompt."""
        system_prompt = (
            f"You are the {task.specialist_name} specialist within the Xeren AI system. "
            f"Your role: {self._get_role_description(task.specialist_id)}. "
            f"Focus exclusively on your specialty. Be precise and structured."
        )

        # Run in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._main_llm.complete(task.sub_task, system=system_prompt, max_tokens=task.max_tokens),
        )
        return response

    def _run_stub(self, task: SpecialistTask) -> str:
        """Return a structured stub output for untrained specialists."""
        return (
            f"[STUB — {task.specialist_name} not yet trained]\n"
            f"Task received: {task.sub_task[:200]}...\n"
            f"When checkpoint is trained at `{self._get_spec(task.specialist_id).checkpoint_dir if self._get_spec(task.specialist_id) else 'unknown'}`, "
            f"this will return real specialist output."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_spec(self, specialist_id: str):
        try:
            sid = SpecialistID(specialist_id)
            return SpecialistRegistry.get(sid)
        except (ValueError, KeyError):
            return None

    def _get_role_description(self, specialist_id: str) -> str:
        descriptions = {
            "M1_understanding":  "Parse intent, extract entities, clarify context",
            "M2_reasoning":      "Apply logical and causal reasoning step-by-step",
            "M3_knowledge":      "Apply factual knowledge and connect concepts",
            "M4_research":       "Find and synthesize information from multiple sources",
            "M5_analysis":       "Break complex information into patterns and insights",
            "M6_planning":       "Create strategies and action sequences",
            "M7_coding":         "Write clean, efficient technical code and creative solutions",
            "M8_simulation":     "Predict outcomes and simulate scenarios before action",
            "M9_critic":         "Find weaknesses, errors, and failure modes",
            "M10_verification":  "Test and validate whether results are correct",
            "M11_optimization":  "Refine and improve solutions for better quality and efficiency",
            "M12_experience":    "Apply learned patterns from past experiences",
            "tool_caller":       "Route tasks to the correct specialist",
        }
        return descriptions.get(specialist_id, "Complete the assigned task")

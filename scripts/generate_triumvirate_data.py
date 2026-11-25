"""Generate Royal Triumvirate Training Dataset.

Executes the TriumvirateTrajectorySynthesizer to generate SFT ChatML trajectories
and DPO preference pairs for fine-tuning Xeren's sovereign leadership models.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xeren.data.synthesizer import (
    TriumvirateTrajectorySynthesizer,
    EXPANDED_FOUNDATIONAL_TASKS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xeren.scripts.generate_data")


def main() -> None:
    output_dir = PROJECT_ROOT / "training" / "data" / "triumvirate"
    synthesizer = TriumvirateTrajectorySynthesizer(output_dir=output_dir)

    logger.info("Starting synthesis of %d diverse Triumvirate tasks...", len(EXPANDED_FOUNDATIONAL_TASKS))
    manifest = synthesizer.export_complete_dataset(EXPANDED_FOUNDATIONAL_TASKS)

    logger.info("=== Dataset Synthesis Complete ===")
    logger.info("Total Tasks Processed: %d", manifest["total_tasks"])
    logger.info("SFT Dataset: %s", manifest["sft_file"])
    logger.info("DPO Dataset: %s", manifest["dpo_file"])
    logger.info("Roles Covered: %s", ", ".join(manifest["roles_covered"]))
    logger.info("Clusters: %s", ", ".join(manifest["clusters_represented"]))


if __name__ == "__main__":
    main()


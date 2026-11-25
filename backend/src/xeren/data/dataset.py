"""Dataset container and I/O utilities for Xeren agent experience data."""

import json
from pathlib import Path
import random
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from xeren.data.schema import DatasetSplit, ExperienceRecord, ReviewStatus
from xeren.data.validator import DatasetValidator, ValidationResult


class ExperienceDataset:
    """In-memory collection of agent experience records with split, validation, and curation support."""

    def __init__(self, records: Optional[List[ExperienceRecord]] = None) -> None:
        self._records: Dict[str, ExperienceRecord] = {}
        self._fingerprints: Dict[str, str] = {}  # fingerprint -> sample_id
        if records:
            for r in records:
                self.add(r)

    def add(
        self,
        record: ExperienceRecord,
        enforce_verified: bool = False,
        prevent_duplicates: bool = True,
    ) -> None:
        """Add an experience record with optional verification and duplicate rejection.

        Runs duplicate detection in O(1) time via an index of content fingerprints.
        """
        if enforce_verified and not record.is_verified:
            raise ValueError(f"Record {record.sample_id} rejected: is_verified is False.")

        if prevent_duplicates:
            if record.sample_id in self._records:
                raise ValueError(f"Duplicate sample_id rejected: {record.sample_id}")
            fp = record.content_fingerprint()
            if fp in self._fingerprints:
                existing_id = self._fingerprints[fp]
                raise ValueError(
                    f"Duplicate content fingerprint rejected: {record.sample_id} matches {existing_id}"
                )

        fp = record.content_fingerprint()
        self._records[record.sample_id] = record
        self._fingerprints[fp] = record.sample_id

    def remove(self, sample_id: str) -> bool:
        """Remove a record by sample_id, cleaning up both records and fingerprint index."""
        if sample_id in self._records:
            rec = self._records.pop(sample_id)
            fp = rec.content_fingerprint()
            self._fingerprints.pop(fp, None)
            return True
        return False

    def get(self, sample_id: str) -> Optional[ExperienceRecord]:
        """Retrieve a record by its sample_id."""
        return self._records.get(sample_id)

    def filter(self, predicate: Callable[[ExperienceRecord], bool]) -> "ExperienceDataset":
        """Filter dataset records based on a predicate function."""
        return ExperienceDataset([r for r in self._records.values() if predicate(r)])

    def filter_for_training(
        self,
        min_quality_score: float = 0.7,
        require_verified: bool = True,
        allow_failures: bool = False,
    ) -> "ExperienceDataset":
        """Filter dataset records to only those eligible for model training."""
        filtered = ExperienceDataset()
        for r in self._records.values():
            eligible, _ = r.is_training_eligible(
                min_quality_score=min_quality_score,
                require_verified=require_verified,
                allow_failures=allow_failures,
            )
            if eligible:
                filtered.add(r)
        return filtered

    def deduplicate(self) -> int:
        """Deduplicate records in-place by fingerprint and ID, keeping first occurrences.

        Returns number of removed duplicates.
        """
        seen_ids: Set[str] = set()
        seen_fps: Set[str] = set()
        kept: List[ExperienceRecord] = []
        removed_count = 0

        for r in self._records.values():
            fp = r.content_fingerprint()
            if r.sample_id in seen_ids or fp in seen_fps:
                removed_count += 1
                continue
            seen_ids.add(r.sample_id)
            seen_fps.add(fp)
            kept.append(r)

        self._records = {r.sample_id: r for r in kept}
        self._fingerprints = {r.content_fingerprint(): r.sample_id for r in kept}
        return removed_count

    def split_train_val_test(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> Tuple["ExperienceDataset", "ExperienceDataset", "ExperienceDataset"]:
        """Deterministically partition records into train, val, and test splits with zero overlap."""
        total_ratio = train_ratio + val_ratio + test_ratio
        if abs(total_ratio - 1.0) > 1e-5:
            raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio:.4f}")

        # Deterministic shuffle: sort by sample_id first to guarantee identical ordering across runs
        records = sorted(list(self._records.values()), key=lambda r: r.sample_id)
        rng = random.Random(seed)
        rng.shuffle(records)

        n = len(records)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_recs = records[:n_train]
        val_recs = records[n_train:n_train + n_val]
        test_recs = records[n_train + n_val:]

        train_ds = ExperienceDataset()
        for r in train_recs:
            r_copy = r.model_copy(update={"split": DatasetSplit.TRAIN})
            train_ds.add(r_copy, prevent_duplicates=False)

        val_ds = ExperienceDataset()
        for r in val_recs:
            r_copy = r.model_copy(update={"split": DatasetSplit.VAL})
            val_ds.add(r_copy, prevent_duplicates=False)

        test_ds = ExperienceDataset()
        for r in test_recs:
            r_copy = r.model_copy(update={"split": DatasetSplit.TEST})
            test_ds.add(r_copy, prevent_duplicates=False)

        return train_ds, val_ds, test_ds

    def summary_stats(self) -> Dict[str, Any]:
        """Compute statistical summary of dataset."""
        total = len(self._records)
        if total == 0:
            return {
                "total_records": 0,
                "splits": {"train": 0, "val": 0, "test": 0},
                "success_count": 0,
                "failure_count": 0,
                "verified_count": 0,
                "unverified_count": 0,
                "review_status": {},
                "avg_quality_score": 0.0,
                "avg_confidence": 0.0,
                "avg_verification_score": 0.0,
                "total_actions": 0,
                "avg_actions_per_record": 0.0,
            }

        recs = list(self._records.values())
        splits: Dict[str, int] = {"train": 0, "val": 0, "test": 0}
        review_status: Dict[str, int] = {}
        success_count = 0
        verified_count = 0
        total_quality = 0.0
        total_conf = 0.0
        total_verif_score = 0.0
        total_actions = 0

        for r in recs:
            s_val = r.split.value if isinstance(r.split, DatasetSplit) else str(r.split)
            splits[s_val] = splits.get(s_val, 0) + 1

            status_val = r.review_status.value if hasattr(r.review_status, "value") else str(r.review_status)
            review_status[status_val] = review_status.get(status_val, 0) + 1

            if r.success:
                success_count += 1
            if r.is_verified:
                verified_count += 1

            total_quality += r.final_quality_score
            total_conf += r.prediction_confidence
            total_verif_score += r.verification.score
            total_actions += len(r.actions)

        return {
            "total_records": total,
            "splits": splits,
            "success_count": success_count,
            "failure_count": total - success_count,
            "verified_count": verified_count,
            "unverified_count": total - verified_count,
            "review_status": review_status,
            "avg_quality_score": round(total_quality / total, 4),
            "avg_confidence": round(total_conf / total, 4),
            "avg_verification_score": round(total_verif_score / total, 4),
            "total_actions": total_actions,
            "avg_actions_per_record": round(total_actions / total, 2),
        }

    def get_split(self, split: Union[DatasetSplit, str]) -> "ExperienceDataset":
        """Get a sub-dataset for a specific partition split ('train', 'val', 'test')."""
        split_val = split.value if isinstance(split, DatasetSplit) else str(split)
        return self.filter(lambda r: r.split.value == split_val)

    def validate(self, validator: Optional[DatasetValidator] = None) -> ValidationResult:
        """Run validation checks on the entire dataset."""
        v = validator or DatasetValidator()
        return v.validate_dataset(list(self._records.values()))

    def to_jsonl(self, file_path: Union[str, Path], split: Optional[Union[DatasetSplit, str]] = None) -> int:
        """Serialize dataset records to a JSONL file. Returns number of written records."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        records = (
            self.get_split(split).records
            if split is not None
            else list(self._records.values())
        )
        with path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")
        return len(records)

    @classmethod
    def from_jsonl(
        cls,
        file_path: Union[str, Path],
        split: Optional[Union[DatasetSplit, str]] = None,
        validator: Optional[DatasetValidator] = None,
        enforce_verified: bool = True,
    ) -> "ExperienceDataset":
        """Load and validate records from a JSONL file."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"JSONL file not found: {file_path}")

        records: List[ExperienceRecord] = []
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                    rec = ExperienceRecord.model_validate(data)
                except Exception as err:
                    raise ValueError(f"Malformed JSONL at {path}:{line_no}: {err}") from err

                if split is not None:
                    target_split = split.value if isinstance(split, DatasetSplit) else str(split)
                    if rec.split.value != target_split:
                        continue

                records.append(rec)

        dataset = cls()
        for r in records:
            dataset.add(r, enforce_verified=enforce_verified, prevent_duplicates=True)

        if validator:
            v_res = dataset.validate(validator)
            if not v_res.is_valid:
                raise ValueError(f"Dataset validation failed: {v_res.errors}")

        return dataset

    @property
    def records(self) -> List[ExperienceRecord]:
        """List of all experience records."""
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[ExperienceRecord]:
        return iter(self._records.values())


def load_jsonl_dataset(
    file_path: Union[str, Path],
    split: Optional[Union[DatasetSplit, str]] = None,
    enforce_verified: bool = True,
) -> ExperienceDataset:
    """Helper to load experience records from JSONL."""
    return ExperienceDataset.from_jsonl(file_path, split=split, enforce_verified=enforce_verified)


def save_jsonl_dataset(
    dataset: ExperienceDataset,
    file_path: Union[str, Path],
    split: Optional[Union[DatasetSplit, str]] = None,
) -> int:
    """Helper to save experience records to JSONL."""
    return dataset.to_jsonl(file_path, split=split)

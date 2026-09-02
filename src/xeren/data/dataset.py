"""Dataset container and I/O utilities for Xeren agent experience data."""

import json
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Union

from xeren.data.schema import DatasetSplit, ExperienceRecord
from xeren.data.validator import DatasetValidator, ValidationResult


class ExperienceDataset:
    """In-memory collection of agent experience records with split and validation support."""

    def __init__(self, records: Optional[List[ExperienceRecord]] = None) -> None:
        self._records: Dict[str, ExperienceRecord] = {}
        if records:
            for r in records:
                self.add(r)

    def add(
        self,
        record: ExperienceRecord,
        enforce_verified: bool = False,
        prevent_duplicates: bool = True,
    ) -> None:
        """Add an experience record with optional verification and duplicate rejection."""
        if enforce_verified and not record.is_verified:
            raise ValueError(f"Record {record.sample_id} rejected: is_verified is False.")

        if prevent_duplicates:
            if record.sample_id in self._records:
                raise ValueError(f"Duplicate sample_id rejected: {record.sample_id}")
            fp = record.content_fingerprint()
            for existing in self._records.values():
                if existing.content_fingerprint() == fp:
                    raise ValueError(
                        f"Duplicate content fingerprint rejected: {record.sample_id} matches {existing.sample_id}"
                    )

        self._records[record.sample_id] = record

    def get(self, sample_id: str) -> Optional[ExperienceRecord]:
        """Retrieve a record by its sample_id."""
        return self._records.get(sample_id)

    def filter(self, predicate: Callable[[ExperienceRecord], bool]) -> "ExperienceDataset":
        """Filter dataset records based on a predicate function."""
        return ExperienceDataset([r for r in self._records.values() if predicate(r)])

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

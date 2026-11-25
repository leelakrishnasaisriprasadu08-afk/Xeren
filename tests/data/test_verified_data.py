"""Integration tests validating the committed JSONL dataset files."""

from pathlib import Path
from xeren.data.dataset import load_jsonl_dataset
from xeren.data.validator import DatasetValidator


def test_verified_datasets_are_valid() -> None:
    data_dir = Path("data")
    assert data_dir.is_dir(), "data/ directory must exist"

    train_path = data_dir / "train.jsonl"
    val_path = data_dir / "val.jsonl"
    test_path = data_dir / "test.jsonl"

    assert train_path.is_file(), "data/train.jsonl must exist"
    assert val_path.is_file(), "data/val.jsonl must exist"
    assert test_path.is_file(), "data/test.jsonl must exist"

    train_ds = load_jsonl_dataset(train_path, split="train", enforce_verified=True)
    val_ds = load_jsonl_dataset(val_path, split="val", enforce_verified=True)
    test_ds = load_jsonl_dataset(test_path, split="test", enforce_verified=True)

    assert len(train_ds) >= 3
    assert len(val_ds) >= 2
    assert len(test_ds) >= 2

    # Validate each individual split
    validator = DatasetValidator(require_verified=True)
    assert train_ds.validate(validator).is_valid is True
    assert val_ds.validate(validator).is_valid is True
    assert test_ds.validate(validator).is_valid is True

    # Validate complete union and split separation
    all_records = train_ds.records + val_ds.records + test_ds.records
    full_result = validator.validate_dataset(all_records, enforce_split_separation=True)
    assert full_result.is_valid is True
    assert full_result.valid_count == len(all_records)
    assert full_result.duplicate_count == 0
    assert full_result.unverified_count == 0

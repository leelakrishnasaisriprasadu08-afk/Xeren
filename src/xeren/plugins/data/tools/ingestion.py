"""Data ingestion tool and pluggable format adapters."""

from abc import ABC, abstractmethod
import csv
import io
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union

from xeren.plugins.data.schemas import (
    ColumnType,
    DataFormat,
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
)

logger = logging.getLogger("xeren.plugins.data.tools.ingestion")

DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_MAX_ROWS = 500_000


class DataIngestionError(Exception):
    """Raised when dataset ingestion fails due to format, path, or size violations."""
    pass


class BaseDataAdapter(ABC):
    """Abstract base class for dataset format adapters."""

    @abstractmethod
    def supports(self, fmt: Union[DataFormat, str]) -> bool:
        """Check if this adapter supports the specified format."""
        pass

    @abstractmethod
    def parse(self, raw_data: Any, options: Optional[Dict[str, Any]] = None) -> StructuredDataset:
        """Parse raw content into a StructuredDataset."""
        pass

    def load(self, raw_data: Any, options: Optional[Dict[str, Any]] = None, **kwargs: Any) -> StructuredDataset:
        """Convenience method loading content from file path, string, or in-memory object."""
        opts = dict(options or {})
        opts.update(kwargs)
        if "dataset_name" in opts and "name" not in opts:
            opts["name"] = opts["dataset_name"]
        if isinstance(raw_data, (str, Path)) and Path(str(raw_data)).is_file():
            content = Path(str(raw_data)).read_text(encoding="utf-8", errors="replace")
            opts.setdefault("name", Path(str(raw_data)).stem)
            return self.parse(content, opts)
        return self.parse(raw_data, opts)


def infer_scalar_type(val: Any) -> ColumnType:
    """Infer ColumnType for an individual scalar value."""
    if val is None or val == "":
        return ColumnType.UNKNOWN
    if isinstance(val, bool):
        return ColumnType.BOOLEAN
    if isinstance(val, int):
        return ColumnType.INTEGER
    if isinstance(val, float):
        return ColumnType.FLOAT
    if isinstance(val, str):
        val_lower = val.strip().lower()
        if val_lower in ("true", "false", "yes", "no"):
            return ColumnType.BOOLEAN
        # Check integer
        if re.match(r"^-?\d+$", val.strip()):
            return ColumnType.INTEGER
        # Check float
        if re.match(r"^-?\d*\.\d+$", val.strip()) or re.match(r"^-?\d+(\.\d*)?[eE]-?\d+$", val.strip()):
            return ColumnType.FLOAT
        # Check datetime
        if re.match(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$", val.strip()):
            return ColumnType.DATETIME
        return ColumnType.STRING
    return ColumnType.OBJECT


def cast_scalar_value(val: Any) -> Any:
    """Cast string representation into native Python scalar if applicable."""
    if val is None:
        return None
    if isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, str):
        s = val.strip()
        if s == "" or s.lower() in ("null", "none", "nan", "na", "#n/a"):
            return None
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
        # Try integer
        if re.match(r"^-?\d+$", s):
            try:
                return int(s)
            except ValueError:
                pass
        # Try float
        if re.match(r"^-?\d*\.\d+$", s) or re.match(r"^-?\d+(\.\d*)?[eE]-?\d+$", s):
            try:
                return float(s)
            except ValueError:
                pass
        return s
    return val


def normalize_headers(headers: Sequence[str]) -> List[str]:
    """Normalize column headers and resolve duplicate names."""
    normalized: List[str] = []
    seen: Dict[str, int] = {}
    for idx, h in enumerate(headers):
        clean_name = (h or "").strip() or f"column_{idx + 1}"
        if clean_name in seen:
            seen[clean_name] += 1
            normalized.append(f"{clean_name}_{seen[clean_name]}")
        else:
            seen[clean_name] = 0
            normalized.append(clean_name)
    return normalized


class CSVDataAdapter(BaseDataAdapter):
    """Adapter for CSV files and strings with delimiter detection and type inference."""

    def supports(self, fmt: Union[DataFormat, str]) -> bool:
        fmt_str = fmt.value if isinstance(fmt, DataFormat) else str(fmt)
        return fmt_str.lower() == "csv"

    def parse(self, raw_data: Any, options: Optional[Dict[str, Any]] = None) -> StructuredDataset:
        opts = options or {}
        if not isinstance(raw_data, str):
            raise DataIngestionError(f"CSVDataAdapter expects string input, got {type(raw_data).__name__}")

        text = raw_data.strip()
        if not text:
            return StructuredDataset(name=opts.get("name", "csv_dataset"), columns=[], rows=[], format=DataFormat.CSV)

        # Detect delimiter if not explicitly provided
        delimiter = opts.get("delimiter")
        if not delimiter:
            first_line = text.split("\n", 1)[0]
            candidates = [",", "\t", ";", "|"]
            counts = {c: first_line.count(c) for c in candidates}
            best = max(counts, key=counts.get)  # type: ignore
            delimiter = best if counts[best] > 0 else ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return StructuredDataset(name=opts.get("name", "csv_dataset"), columns=[], rows=[], format=DataFormat.CSV)

        columns = normalize_headers(raw_headers)
        rows: List[Dict[str, Any]] = []

        auto_cast = opts.get("auto_cast", True)
        for raw_row in reader:
            if not raw_row or (len(raw_row) == 1 and not raw_row[0].strip()):
                continue
            row_dict: Dict[str, Any] = {}
            for col_idx, col_name in enumerate(columns):
                raw_val = raw_row[col_idx] if col_idx < len(raw_row) else None
                row_dict[col_name] = cast_scalar_value(raw_val) if auto_cast else raw_val
            rows.append(row_dict)

        return StructuredDataset(
            name=opts.get("name", "csv_dataset"),
            columns=columns,
            rows=rows,
            format=DataFormat.CSV,
        )


class JSONDataAdapter(BaseDataAdapter):
    """Adapter for JSON records and columnar JSON payloads."""

    def supports(self, fmt: Union[DataFormat, str]) -> bool:
        fmt_str = fmt.value if isinstance(fmt, DataFormat) else str(fmt)
        return fmt_str.lower() in ("json", "jsonl")

    def parse(self, raw_data: Any, options: Optional[Dict[str, Any]] = None) -> StructuredDataset:
        opts = options or {}
        parsed_data = raw_data
        if isinstance(raw_data, str):
            text = raw_data.strip()
            if not text:
                return StructuredDataset(name=opts.get("name", "json_dataset"), columns=[], rows=[], format=DataFormat.JSON)
            try:
                parsed_data = json.loads(text)
            except Exception as err:
                # Try parsing as JSONL
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                records = []
                try:
                    for l in lines:
                        records.append(json.loads(l))
                    parsed_data = records
                except Exception:
                    raise DataIngestionError(f"Failed to parse JSON payload: {err}") from err

        # Case 1: List of dicts (records orientation)
        if isinstance(parsed_data, list):
            if not parsed_data:
                return StructuredDataset(name=opts.get("name", "json_dataset"), columns=[], rows=[], format=DataFormat.JSON)
            columns: List[str] = []
            for item in parsed_data:
                if isinstance(item, dict):
                    for k in item.keys():
                        if k not in columns:
                            columns.append(k)
            rows = [dict(item) if isinstance(item, dict) else {"value": item} for item in parsed_data]
            return StructuredDataset(
                name=opts.get("name", "json_dataset"),
                columns=columns or ["value"],
                rows=rows,
                format=DataFormat.JSON,
            )

        # Case 2: Dict of lists (columnar orientation)
        if isinstance(parsed_data, dict):
            columns = list(parsed_data.keys())
            if not columns:
                return StructuredDataset(name=opts.get("name", "json_dataset"), columns=[], rows=[], format=DataFormat.JSON)

            # Check if values are lists
            first_val = parsed_data[columns[0]]
            if isinstance(first_val, list):
                num_rows = len(first_val)
                rows = []
                for idx in range(num_rows):
                    row: Dict[str, Any] = {}
                    for col in columns:
                        col_list = parsed_data[col]
                        row[col] = col_list[idx] if isinstance(col_list, list) and idx < len(col_list) else None
                    rows.append(row)
                return StructuredDataset(
                    name=opts.get("name", "json_dataset"),
                    columns=columns,
                    rows=rows,
                    format=DataFormat.JSON,
                )
            else:
                # Single record dictionary
                return StructuredDataset(
                    name=opts.get("name", "json_dataset"),
                    columns=columns,
                    rows=[parsed_data],
                    format=DataFormat.JSON,
                )

        raise DataIngestionError(f"Unsupported JSON data structure: {type(parsed_data).__name__}")


class DictDataAdapter(BaseDataAdapter):
    """Adapter for in-memory lists of dictionary records."""

    def supports(self, fmt: Union[DataFormat, str]) -> bool:
        fmt_str = fmt.value if isinstance(fmt, DataFormat) else str(fmt)
        return fmt_str.lower() in ("dict", "records")

    def parse(self, raw_data: Any, options: Optional[Dict[str, Any]] = None) -> StructuredDataset:
        opts = options or {}
        if not isinstance(raw_data, list):
            raise DataIngestionError(f"DictDataAdapter expects a list of dictionaries, got {type(raw_data).__name__}")

        columns: List[str] = []
        for r in raw_data:
            if isinstance(r, dict):
                for k in r.keys():
                    if k not in columns:
                        columns.append(k)

        rows = [dict(r) if isinstance(r, dict) else {"value": r} for r in raw_data]
        return StructuredDataset(
            name=opts.get("name", "dict_dataset"),
            columns=columns or ["value"],
            rows=rows,
            format=DataFormat.DICT,
        )


class DataIngestionTool:
    """Coordinates format adapters and safely loads datasets with size bounds and security checks."""

    def __init__(
        self,
        adapters: Optional[List[BaseDataAdapter]] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_rows: int = DEFAULT_MAX_ROWS,
        base_dir: Optional[Path] = None,
    ) -> None:
        self.adapters: List[BaseDataAdapter] = adapters or [
            CSVDataAdapter(),
            JSONDataAdapter(),
            DictDataAdapter(),
        ]
        self.max_bytes = max_bytes
        self.max_rows = max_rows
        self.base_dir = base_dir or Path.cwd()

    def register_adapter(self, adapter: BaseDataAdapter) -> None:
        """Register a new format adapter (e.g. Excel or SQL)."""
        self.adapters.insert(0, adapter)

    def is_safe_path(self, target_path: Union[str, Path]) -> bool:
        """Check if path is safe and does not traverse outside allowed directories."""
        try:
            raw_str = str(target_path).replace("\\", "/")
            if ".." in raw_str:
                return False
            resolved = (self.base_dir / target_path).resolve()
            # Prevent reading sensitive system directories
            path_str = str(resolved).lower()
            if any(s in path_str for s in ("windows\\system32", "etc/shadow", "etc/passwd", ".ssh")):
                return False
            return True
        except Exception:
            return False

    def ingest(
        self,
        data: Optional[Union[str, List[Dict[str, Any]], Dict[str, Any]]] = None,
        file_path: Optional[str] = None,
        dataset: Optional[StructuredDataset] = None,
        format_hint: Optional[Union[DataFormat, str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> StructuredDataset:
        """Ingest data from pre-existing dataset, in-memory payload, or local file."""
        opts = options or {}

        # 1. If already a StructuredDataset, return directly
        if dataset is not None:
            return dataset

        # 2. Ingest from file if provided
        if file_path is not None:
            if not self.is_safe_path(file_path):
                raise DataIngestionError(f"Security violation: Path traversal detected in file path '{file_path}'")

            path = (self.base_dir / file_path).resolve() if not Path(file_path).is_absolute() else Path(file_path)
            if not path.is_file():
                raise DataIngestionError(f"Dataset file not found: '{file_path}'")

            file_size = path.stat().st_size
            if file_size > self.max_bytes:
                raise DataIngestionError(f"Dataset file size ({file_size} bytes) exceeds limit ({self.max_bytes} bytes)")

            content = path.read_text(encoding="utf-8", errors="replace")
            ext = path.suffix.lstrip(".").lower()
            inferred_format = format_hint or ext
            opts.setdefault("name", path.stem)
            return self._dispatch_parse(content, inferred_format, opts)

        # 3. Ingest from in-memory data
        if data is not None:
            if isinstance(data, list):
                return self._dispatch_parse(data, format_hint or DataFormat.DICT, opts)
            elif isinstance(data, dict):
                return self._dispatch_parse(data, format_hint or DataFormat.JSON, opts)
            elif isinstance(data, str):
                if len(data.encode("utf-8")) > self.max_bytes:
                    raise DataIngestionError(f"Data payload size exceeds limit ({self.max_bytes} bytes)")
                inferred = format_hint or self._infer_string_format(data)
                return self._dispatch_parse(data, inferred, opts)

        raise DataIngestionError("No data, file_path, or dataset provided for ingestion.")

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute ingestion on a DataInput payload."""
        try:
            ds = self.ingest(
                data=input_data.data or input_data.records,
                file_path=input_data.file_path,
                dataset=input_data.dataset,
                format_hint=input_data.format,
                options=input_data.metadata,
            )
            return DataResult(
                operation=DataOperation.INGEST,
                success=True,
                dataset=ds,
                stats={"rows": ds.row_count, "columns": ds.column_count},
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.INGEST,
                success=False,
                error=str(err),
            )

    def _infer_string_format(self, text: str) -> str:
        """Heuristically determine if a string is JSON or CSV."""
        trimmed = text.strip()
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
            return "json"
        return "csv"

    def _dispatch_parse(self, raw_data: Any, fmt: Union[DataFormat, str], options: Dict[str, Any]) -> StructuredDataset:
        """Find matching adapter and parse data, enforcing row bounds."""
        for adapter in self.adapters:
            if adapter.supports(fmt):
                ds = adapter.parse(raw_data, options=options)
                if ds.row_count > self.max_rows:
                    raise DataIngestionError(f"Dataset rows ({ds.row_count}) exceeds limit ({self.max_rows})")
                return ds

        raise DataIngestionError(f"No adapter available to ingest format: '{fmt}'")


__all__ = [
    "DataIngestionError",
    "BaseDataAdapter",
    "CSVDataAdapter",
    "JSONDataAdapter",
    "DictDataAdapter",
    "DataIngestionTool",
    "infer_scalar_type",
    "cast_scalar_value",
    "normalize_headers",
]

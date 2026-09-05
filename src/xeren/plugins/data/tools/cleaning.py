"""Data cleaning tool providing safe deduplication, imputation, filtering, and type casting."""

from collections import Counter
import logging
import statistics
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from xeren.plugins.data.schemas import (
    CleaningReport,
    CleaningRule,
    ColumnType,
    DataInput,
    DataOperation,
    DataResult,
    StructuredDataset,
)

logger = logging.getLogger("xeren.plugins.data.tools.cleaning")


class DataCleaningTool:
    """Performs deterministic, rule-based data cleaning on StructuredDatasets."""

    def clean(
        self,
        dataset: StructuredDataset,
        rules: Optional[Union[CleaningRule, Sequence[CleaningRule]]] = None,
    ) -> Tuple[StructuredDataset, CleaningReport]:
        """Apply cleaning rules to the dataset and return the cleaned dataset and report."""
        rule_cfg = self._normalize_rules(rules)
        initial_rows = dataset.row_count
        operations_applied: List[str] = []

        current_columns = list(dataset.columns)
        current_rows: List[Dict[str, Any]] = [dict(r) for r in dataset.rows]

        duplicates_removed = 0
        missing_dropped = 0
        missing_imputed = 0

        # 1. Strip whitespace from string values
        if rule_cfg.strip_strings:
            for r in current_rows:
                for col in current_columns:
                    val = r.get(col)
                    if isinstance(val, str):
                        r[col] = val.strip()
            operations_applied.append("strip_strings")

        # 2. Drop duplicate rows
        if rule_cfg.drop_duplicates:
            seen_hashes: Set[int] = set()
            deduped_rows: List[Dict[str, Any]] = []
            for r in current_rows:
                row_key = hash(tuple(sorted((k, str(v)) for k, v in r.items())))
                if row_key not in seen_hashes:
                    seen_hashes.add(row_key)
                    deduped_rows.append(r)
                else:
                    duplicates_removed += 1
            current_rows = deduped_rows
            operations_applied.append(f"drop_duplicates (removed {duplicates_removed})")

        # 3. Drop all-missing rows
        if rule_cfg.drop_all_missing_rows:
            kept_rows: List[Dict[str, Any]] = []
            for r in current_rows:
                if any(r.get(c) is not None and r.get(c) != "" for c in current_columns):
                    kept_rows.append(r)
                else:
                    missing_dropped += 1
            current_rows = kept_rows
            operations_applied.append(f"drop_all_missing_rows (dropped {missing_dropped})")

        # 4. Drop rows with missing values in specific columns
        if rule_cfg.drop_missing_columns:
            target_cols = [c for c in rule_cfg.drop_missing_columns if c in current_columns]
            kept_rows = []
            dropped_for_cols = 0
            for r in current_rows:
                if all(r.get(c) is not None and r.get(c) != "" for c in target_cols):
                    kept_rows.append(r)
                else:
                    dropped_for_cols += 1
            current_rows = kept_rows
            missing_dropped += dropped_for_cols
            operations_applied.append(f"drop_missing_columns: {target_cols} (dropped {dropped_for_cols})")

        # 5. Impute / fill missing values
        if rule_cfg.fill_missing:
            for col, strategy in rule_cfg.fill_missing.items():
                if col not in current_columns:
                    continue

                col_values = [r.get(col) for r in current_rows if r.get(col) is not None and r.get(col) != ""]
                fill_val: Any = strategy

                if isinstance(strategy, str):
                    strat_lower = strategy.strip().lower()
                    numeric_vals = [v for v in col_values if isinstance(v, (int, float))]
                    if strat_lower == "mean" and numeric_vals:
                        fill_val = statistics.mean(numeric_vals)
                    elif strat_lower == "median" and numeric_vals:
                        fill_val = statistics.median(numeric_vals)
                    elif strat_lower == "mode" and col_values:
                        counts = Counter(col_values)
                        fill_val = counts.most_common(1)[0][0]

                imputed_in_col = 0
                for r in current_rows:
                    if r.get(col) is None or r.get(col) == "":
                        r[col] = fill_val
                        imputed_in_col += 1

                missing_imputed += imputed_in_col
                operations_applied.append(f"fill_missing: {col} -> {fill_val} ({imputed_in_col} cells)")

        # 6. Column renames
        if rule_cfg.column_renames:
            renamed_columns = []
            for col in current_columns:
                new_name = rule_cfg.column_renames.get(col, col)
                renamed_columns.append(new_name)

            for r in current_rows:
                for old_col, new_col in rule_cfg.column_renames.items():
                    if old_col in r and old_col != new_col:
                        r[new_col] = r.pop(old_col)

            current_columns = renamed_columns
            operations_applied.append(f"column_renames: {rule_cfg.column_renames}")

        # 7. Type casting
        if rule_cfg.cast_types:
            for col, target_type in rule_cfg.cast_types.items():
                if col not in current_columns:
                    continue
                type_name = target_type.value if isinstance(target_type, ColumnType) else str(target_type).lower()
                for r in current_rows:
                    val = r.get(col)
                    if val is not None and val != "":
                        try:
                            if type_name in ("int", "integer"):
                                r[col] = int(float(val))
                            elif type_name in ("float", "double", "number"):
                                r[col] = float(val)
                            elif type_name in ("str", "string", "text"):
                                r[col] = str(val)
                            elif type_name in ("bool", "boolean"):
                                r[col] = bool(val)
                        except (ValueError, TypeError):
                            pass
            operations_applied.append(f"cast_types: {rule_cfg.cast_types}")

        cleaned_dataset = StructuredDataset(
            name=f"{dataset.name}_cleaned",
            columns=current_columns,
            rows=current_rows,
            format=dataset.format,
        )

        report = CleaningReport(
            initial_rows=initial_rows,
            cleaned_rows=cleaned_dataset.row_count,
            duplicates_removed=duplicates_removed,
            missing_imputed=missing_imputed,
            missing_dropped=missing_dropped,
            operations_applied=operations_applied,
        )

        return cleaned_dataset, report

    def _normalize_rules(
        self, rules: Optional[Union[CleaningRule, Sequence[CleaningRule]]]
    ) -> CleaningRule:
        """Normalize various input formats of cleaning rules into a unified CleaningRule."""
        if rules is None:
            return CleaningRule()

        if isinstance(rules, CleaningRule) and rules.rule_type is None:
            return rules

        rule_list = [rules] if isinstance(rules, CleaningRule) else list(rules)

        # Build composite CleaningRule from list
        cfg = CleaningRule(
            drop_duplicates=False,
            strip_strings=False,
            fill_missing={},
            column_renames={},
            cast_types={},
        )

        for r in rule_list:
            rtype = (r.rule_type or "").lower()
            params = r.parameters or {}

            if rtype in ("drop_duplicates", "deduplicate"):
                cfg.drop_duplicates = True
            elif rtype in ("trim_strings", "strip_strings"):
                cfg.strip_strings = True
            elif rtype in ("drop_all_missing_rows",):
                cfg.drop_all_missing_rows = True
            elif rtype in ("drop_missing_columns",):
                cols = params.get("columns") or ([r.column] if r.column else [])
                cfg.drop_missing_columns = cols
            elif rtype in ("impute_missing", "fill_missing"):
                if r.column:
                    strat = params.get("strategy", "mean")
                    if strat == "constant":
                        val = params.get("value")
                    else:
                        val = strat
                    if cfg.fill_missing is None:
                        cfg.fill_missing = {}
                    cfg.fill_missing[r.column] = val
            elif rtype in ("rename_columns", "rename"):
                mapping = params.get("mapping", {})
                if cfg.column_renames is None:
                    cfg.column_renames = {}
                cfg.column_renames.update(mapping)
            elif rtype in ("cast_types", "cast"):
                casts = params.get("casts", {})
                if cfg.cast_types is None:
                    cfg.cast_types = {}
                cfg.cast_types.update(casts)

        return cfg

    def execute(self, input_data: DataInput) -> DataResult:
        """Execute cleaning on a DataInput payload."""
        try:
            dataset = input_data.dataset
            if dataset is None:
                from xeren.plugins.data.tools.ingestion import DataIngestionTool
                dataset = DataIngestionTool().ingest(
                    data=input_data.data or input_data.records,
                    file_path=input_data.file_path,
                    format_hint=input_data.format,
                    options=input_data.metadata,
                )
            cleaned_ds, report = self.clean(dataset, rules=input_data.cleaning_rules)
            return DataResult(
                operation=DataOperation.CLEAN,
                success=True,
                dataset=cleaned_ds,
                cleaning=report,
                stats={"initial_rows": report.initial_rows, "cleaned_rows": report.cleaned_rows},
            )
        except Exception as err:
            return DataResult(
                operation=DataOperation.CLEAN,
                success=False,
                error=str(err),
            )


__all__ = ["DataCleaningTool"]

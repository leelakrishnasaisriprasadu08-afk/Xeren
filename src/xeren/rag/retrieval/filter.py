"""Metadata filtering models and evaluation engine for RAG retrieval."""

from enum import Enum
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field


class FilterOperator(str, Enum):
    """Operators supported in metadata filter conditions."""

    EQ = "eq"          # Exact equality (==)
    NEQ = "neq"        # Not equal (!=)
    IN = "in"          # Value in collection
    NIN = "nin"        # Value not in collection
    CONTAINS = "contains"  # Substring or item in list
    GT = "gt"          # Greater than (>)
    GTE = "gte"        # Greater than or equal (>=)
    LT = "lt"          # Less than (<)
    LTE = "lte"        # Less than or equal (<=)


class FilterCondition(BaseModel):
    """A single conditional expression on a metadata field."""

    field: str = Field(..., description="Target metadata attribute key")
    operator: FilterOperator = Field(default=FilterOperator.EQ, description="Comparison operator")
    value: Any = Field(..., description="Target value to compare against")

    def evaluate(self, metadata: Dict[str, Any]) -> bool:
        """Evaluate this condition against a metadata dictionary."""
        if self.field not in metadata:
            return False

        target = metadata[self.field]

        if self.operator == FilterOperator.EQ:
            return target == self.value
        elif self.operator == FilterOperator.NEQ:
            return target != self.value
        elif self.operator == FilterOperator.IN:
            return target in self.value if hasattr(self.value, "__contains__") else False
        elif self.operator == FilterOperator.NIN:
            return target not in self.value if hasattr(self.value, "__contains__") else True
        elif self.operator == FilterOperator.CONTAINS:
            if isinstance(target, (list, set, tuple)):
                return self.value in target
            if isinstance(target, str):
                return str(self.value) in target
            return False
        elif self.operator == FilterOperator.GT:
            return target > self.value
        elif self.operator == FilterOperator.GTE:
            return target >= self.value
        elif self.operator == FilterOperator.LT:
            return target < self.value
        elif self.operator == FilterOperator.LTE:
            return target <= self.value

        return False


class MetadataFilter(BaseModel):
    """A composite metadata filter containing one or more conditions."""

    conditions: List[FilterCondition] = Field(default_factory=list, description="List of filter conditions")
    logic: Literal["AND", "OR"] = Field(default="AND", description="Boolean evaluation logic across conditions")

    @classmethod
    def eq(cls, field: str, value: Any) -> "MetadataFilter":
        """Convenience factory for single equality condition."""
        return cls(conditions=[FilterCondition(field=field, operator=FilterOperator.EQ, value=value)])

    @classmethod
    def in_list(cls, field: str, values: List[Any]) -> "MetadataFilter":
        """Convenience factory for IN condition."""
        return cls(conditions=[FilterCondition(field=field, operator=FilterOperator.IN, value=values)])

    def matches(self, metadata: Dict[str, Any]) -> bool:
        """Evaluate if the given metadata satisfies all filter conditions."""
        if not self.conditions:
            return True

        if self.logic == "AND":
            return all(cond.evaluate(metadata) for cond in self.conditions)
        else:
            return any(cond.evaluate(metadata) for cond in self.conditions)

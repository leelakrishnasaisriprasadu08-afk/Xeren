"""Unit tests for MetadataFilter and FilterCondition."""

from xeren.rag.retrieval.filter import FilterCondition, FilterOperator, MetadataFilter


def test_filter_condition_eq_and_neq() -> None:
    cond_eq = FilterCondition(field="author", operator=FilterOperator.EQ, value="Alice")
    assert cond_eq.evaluate({"author": "Alice"}) is True
    assert cond_eq.evaluate({"author": "Bob"}) is False
    assert cond_eq.evaluate({}) is False

    cond_neq = FilterCondition(field="author", operator=FilterOperator.NEQ, value="Alice")
    assert cond_neq.evaluate({"author": "Bob"}) is True
    assert cond_neq.evaluate({"author": "Alice"}) is False


def test_filter_condition_in_and_nin() -> None:
    cond_in = FilterCondition(field="status", operator=FilterOperator.IN, value=["draft", "published"])
    assert cond_in.evaluate({"status": "published"}) is True
    assert cond_in.evaluate({"status": "archived"}) is False

    cond_nin = FilterCondition(field="status", operator=FilterOperator.NIN, value=["draft", "published"])
    assert cond_nin.evaluate({"status": "archived"}) is True
    assert cond_nin.evaluate({"status": "draft"}) is False


def test_filter_condition_contains() -> None:
    # String containment
    cond_str = FilterCondition(field="path", operator=FilterOperator.CONTAINS, value="guide")
    assert cond_str.evaluate({"path": "/docs/ml_guide.md"}) is True
    assert cond_str.evaluate({"path": "/docs/readme.txt"}) is False

    # List containment
    cond_list = FilterCondition(field="tags", operator=FilterOperator.CONTAINS, value="ai")
    assert cond_list.evaluate({"tags": ["ai", "python"]}) is True
    assert cond_list.evaluate({"tags": ["security"]}) is False


def test_filter_condition_comparisons() -> None:
    cond_gt = FilterCondition(field="score", operator=FilterOperator.GT, value=80)
    assert cond_gt.evaluate({"score": 90}) is True
    assert cond_gt.evaluate({"score": 80}) is False

    cond_lte = FilterCondition(field="score", operator=FilterOperator.LTE, value=80)
    assert cond_lte.evaluate({"score": 80}) is True
    assert cond_lte.evaluate({"score": 81}) is False


def test_metadata_filter_and_logic() -> None:
    filter_and = MetadataFilter(
        conditions=[
            FilterCondition(field="author", operator=FilterOperator.EQ, value="Alice"),
            FilterCondition(field="year", operator=FilterOperator.GTE, value=2024),
        ],
        logic="AND",
    )
    assert filter_and.matches({"author": "Alice", "year": 2025}) is True
    assert filter_and.matches({"author": "Alice", "year": 2023}) is False
    assert filter_and.matches({"author": "Bob", "year": 2025}) is False


def test_metadata_filter_or_logic() -> None:
    filter_or = MetadataFilter(
        conditions=[
            FilterCondition(field="dept", operator=FilterOperator.EQ, value="AI"),
            FilterCondition(field="dept", operator=FilterOperator.EQ, value="Core"),
        ],
        logic="OR",
    )
    assert filter_or.matches({"dept": "AI"}) is True
    assert filter_or.matches({"dept": "Core"}) is True
    assert filter_or.matches({"dept": "Sales"}) is False

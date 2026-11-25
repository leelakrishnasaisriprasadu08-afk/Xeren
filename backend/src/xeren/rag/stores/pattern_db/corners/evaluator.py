"""
Xeren Sovereign Pattern DB — Multi-Corner Diagnostics & Golden Evaluator
========================================================================
Measures Recall@k and Routing Accuracy per pattern corner separately.
Pinpoints exactly which corner (e.g. failure_fix or intent_solution) is failing
so developers can tune retrieval parameters with high precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .models import PatternCorner
from .router import PatternQueryRouter
from .store import MultiCornerPatternStore


@dataclass
class CornerMetrics:
    """Evaluation metrics for a specific pattern corner."""

    corner: PatternCorner
    total_queries: int
    routing_accuracy: float
    recall_at_1: float
    recall_at_3: float
    status: str  # "HEALTHY", "DEGRADED", "FAILING"


class PatternCornerEvaluator:
    """Runs automated diagnostics across all pattern corners using a curated golden set."""

    GOLDEN_DATASET: List[Dict[str, Any]] = [
        # 1. Failure -> Fix Queries
        {
            "query": "Fix PermissionError errno 13 permission denied on file write",
            "corner": PatternCorner.FAILURE_FIX,
            "expected_signature_substr": "permission",
        },
        {
            "query": "Resolve execution timed out deadline exceeded in worker pool",
            "corner": PatternCorner.FAILURE_FIX,
            "expected_signature_substr": "time",
        },
        {
            "query": "Fix syntax error unexpected token line 42 in python function",
            "corner": PatternCorner.FAILURE_FIX,
            "expected_signature_substr": "syntax",
        },
        # 2. Workflow Definitions
        {
            "query": "Find workflow for user onboarding and database provisioning",
            "corner": PatternCorner.WORKFLOW,
            "expected_signature_substr": "onboard",
        },
        {
            "query": "Show steps to deploy backend service to production",
            "corner": PatternCorner.WORKFLOW,
            "expected_signature_substr": "deploy",
        },
        # 3. Rules & Permissions
        {
            "query": "Can the coding agent delete system files in workspace root?",
            "corner": PatternCorner.RULES_PERMISSIONS,
            "expected_signature_substr": "delete",
        },
        {
            "query": "What permissions are required to execute terminal shell commands?",
            "corner": PatternCorner.RULES_PERMISSIONS,
            "expected_signature_substr": "terminal",
        },
        # 4. Tool Schemas
        {
            "query": "What are the arguments for the python ast parser tool?",
            "corner": PatternCorner.TOOL_SCHEMA,
            "expected_signature_substr": "ast",
        },
        {
            "query": "Find tool schema for executing database sql queries",
            "corner": PatternCorner.TOOL_SCHEMA,
            "expected_signature_substr": "sql",
        },
        # 5. Intent -> Solution Cases
        {
            "query": "How to generate weekly executive revenue analytics report",
            "corner": PatternCorner.INTENT_SOLUTION,
            "expected_signature_substr": "report",
        },
        {
            "query": "Automated workflow to backup postgres database snapshot",
            "corner": PatternCorner.INTENT_SOLUTION,
            "expected_signature_substr": "backup",
        },
    ]

    @classmethod
    def evaluate_store(cls, store: MultiCornerPatternStore) -> Dict[str, Any]:
        """Run golden evaluation queries and compute per-corner recall and routing accuracy."""
        corner_queries: Dict[PatternCorner, List[Dict[str, Any]]] = {c: [] for c in PatternCorner}
        for item in cls.GOLDEN_DATASET:
            corner_queries[item["corner"]].append(item)

        results: Dict[str, Any] = {
            "overall_routing_accuracy": 0.0,
            "corner_breakdown": {},
            "failing_corners": [],
        }

        total_correct_routes = 0
        total_eval_queries = 0

        for corner, test_cases in corner_queries.items():
            if not test_cases:
                continue

            r_hits = 0
            rec_1_hits = 0
            rec_3_hits = 0

            for tc in test_cases:
                total_eval_queries += 1
                q = tc["query"]
                exp_corner = tc["corner"]

                # 1. Evaluate Router
                routes = PatternQueryRouter.route(q)
                top_routed = [c for c, _ in routes[:2]]
                if exp_corner in top_routed:
                    r_hits += 1
                    total_correct_routes += 1

                # 2. Evaluate Retrieval
                hits = store.query(q, top_k=3, target_corner=exp_corner)
                if hits:
                    rec_3_hits += 1
                    if hits[0].corner == exp_corner:
                        rec_1_hits += 1

            routing_acc = r_hits / len(test_cases)
            recall_1 = rec_1_hits / len(test_cases)
            recall_3 = rec_3_hits / len(test_cases)

            status = "HEALTHY"
            if recall_3 < 0.60 or routing_acc < 0.70:
                status = "FAILING"
                results["failing_corners"].append(corner.value)
            elif recall_3 < 0.85:
                status = "DEGRADED"

            results["corner_breakdown"][corner.value] = {
                "queries_evaluated": len(test_cases),
                "routing_accuracy": round(routing_acc, 2),
                "recall_at_1": round(recall_1, 2),
                "recall_at_3": round(recall_3, 2),
                "health": status,
            }

        if total_eval_queries > 0:
            results["overall_routing_accuracy"] = round(total_correct_routes / total_eval_queries, 2)

        return results

    @classmethod
    def seed_golden_records(cls, store: MultiCornerPatternStore) -> None:
        """Seed representative records for all golden evaluation queries."""
        # 1. Failure Fix records
        store.ingest_pattern(
            corner=PatternCorner.FAILURE_FIX,
            raw_data={
                "error": "PermissionError: [Errno 13] Permission denied on file write: '/workspace/protected.py'",
                "solution": "Adjust sandbox permissions or request elevated grant for write.",
                "root_cause": "Filesystem permission restriction",
            },
            summary="Permission denied errno 13 error during file write resolution",
            success=True,
        )
        store.ingest_pattern(
            corner=PatternCorner.FAILURE_FIX,
            raw_data={
                "error": "TimeoutError: execution timed out deadline exceeded in worker pool",
                "solution": "Increase worker pool timeout limit or batch smaller chunks.",
                "root_cause": "Worker task deadline exceeded",
            },
            summary="Worker pool deadline exceeded and execution timed out fix",
            success=True,
        )
        store.ingest_pattern(
            corner=PatternCorner.FAILURE_FIX,
            raw_data={
                "error": "SyntaxError: unexpected token line 42 in python function",
                "solution": "Balance mismatched closing brackets or colons on line 42.",
                "root_cause": "Python syntax parsing error",
            },
            summary="Python syntax error unexpected token on line 42 resolution",
            success=True,
        )

        # 2. Workflow definitions
        wf1 = store.ingest_pattern(
            corner=PatternCorner.WORKFLOW,
            raw_data={
                "name": "User Onboarding",
                "goal": "user onboarding and database provisioning",
                "steps": [
                    {"action": "create_user_record"},
                    {"action": "assign_tenant_roles"},
                    {"action": "provision_database_schema"},
                ],
            },
            summary="DAG steps for user onboarding and database provisioning pipeline",
            success=True,
        )
        store.ingest_pattern(
            corner=PatternCorner.WORKFLOW,
            raw_data={
                "name": "Production Deploy",
                "goal": "deploy backend service to production",
                "steps": [
                    {"action": "run_linter_and_tests"},
                    {"action": "build_container_image"},
                    {"action": "rolling_service_deploy"},
                ],
            },
            summary="Steps to deploy backend service to production environments",
            success=True,
        )

        # 3. Rules & Permissions
        store.ingest_pattern(
            corner=PatternCorner.RULES_PERMISSIONS,
            raw_data={
                "subject": "coding agent",
                "action": "delete system files in workspace root",
                "resource": "workspace root",
                "allowed": False,
            },
            summary="Coding agent forbidden from deleting system files in workspace root",
            success=True,
        )
        store.ingest_pattern(
            corner=PatternCorner.RULES_PERMISSIONS,
            raw_data={
                "subject": "agent",
                "action": "execute terminal shell commands",
                "resource": "terminal",
                "allowed": True,
            },
            summary="Permissions required to execute terminal shell commands",
            success=True,
        )

        # 4. Tool Schemas
        store.ingest_pattern(
            corner=PatternCorner.TOOL_SCHEMA,
            raw_data={
                "name": "python_ast_parser",
                "description": "python ast parser tool to extract functions, classes, and call trees",
                "parameters": {"code_content": "str", "depth": "int"},
            },
            summary="Python AST parser tool schema and arguments",
            success=True,
        )
        store.ingest_pattern(
            corner=PatternCorner.TOOL_SCHEMA,
            raw_data={
                "name": "sql_query_executor",
                "description": "tool schema for executing database sql queries securely",
                "parameters": {"query": "str", "database": "str"},
            },
            summary="Tool schema for executing database SQL queries",
            success=True,
        )

        # 5. Intent -> Solution Cases
        store.ingest_pattern(
            corner=PatternCorner.INTENT_SOLUTION,
            raw_data={
                "intent": "generate weekly executive revenue analytics report",
                "solution_workflow_id": "wf-exec-revenue-42",
            },
            summary="Intent mapping for weekly executive revenue analytics report",
            success=True,
            parent_workflow_id=wf1.pattern_id,
        )
        store.ingest_pattern(
            corner=PatternCorner.INTENT_SOLUTION,
            raw_data={
                "intent": "backup postgres database snapshot automated workflow",
                "solution_workflow_id": "wf-pg-backup-101",
            },
            summary="Intent mapping to automated workflow to backup postgres database snapshot",
            success=True,
        )

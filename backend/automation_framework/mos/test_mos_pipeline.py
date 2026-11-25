"""
Xeren MoS — End-to-End Smoke Test
Tests the full dispatch pipeline:
  DispatchRequest → ToolCaller → SpecialistRunner → AggregatedResponse

Works WITHOUT any trained specialist checkpoints (uses STUB mode).
"""
import asyncio
import sys
from pathlib import Path

# Make sure project root, backend, and backend/src are in path
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "src"))

from automation_framework.mos import (
    DispatchRequest,
    SpecialistRegistry,
    ToolCaller,
    SpecialistRunner,
    TaskStatus,
)


async def test_tool_caller_routing():
    print("=" * 60)
    print("TEST 1: ToolCaller routing — coding + reasoning task")
    print("=" * 60)

    runner = SpecialistRunner(main_llm=None)   # No LLM = STUB mode
    tool_caller = ToolCaller(runner=runner)

    request = DispatchRequest(
        user_query="Write a Python function to sort a list using merge sort and explain the time complexity",
        task_description="Implement merge sort and explain time complexity",
        required_capabilities=["coding", "reasoning"],
        allow_parallel=True,
        max_specialists=3,
    )

    response = await tool_caller.dispatch(request)

    print(f"  Trace ID: {response.dispatch_trace_id}")
    print(f"  Status: {response.status}")
    print(f"  Specialists used: {response.total_specialists_used}")
    print(f"  Execution: {response.total_execution_ms:.1f}ms")
    print(f"  Warnings: {response.warnings}")
    print()
    for r in response.specialist_results:
        print(f"  [{r.specialist_id}] status={r.status} confidence={r.confidence}")
        print(f"    {r.output[:120]}")
    print()
    assert response.status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED), f"Unexpected status: {response.status}"
    print("  ✅ PASSED\n")


async def test_registry_lookup():
    print("=" * 60)
    print("TEST 2: SpecialistRegistry capability lookup")
    print("=" * 60)

    tests = [
        ("code",     "M7_coding"),
        ("reason",   "M2_reasoning"),
        ("plan",     "M6_planning"),
        ("research", "M4_research"),
        ("verify",   "M10_verification"),
    ]
    for keyword, expected_id in tests:
        matches = SpecialistRegistry.find_by_capability(keyword)
        ids = [m.id.value for m in matches]
        assert expected_id in ids, f"Expected {expected_id} in {ids} for keyword '{keyword}'"
        print(f"  '{keyword}' → {ids[0]} ✅")
    print()


async def test_parallel_vs_sequential():
    print("=" * 60)
    print("TEST 3: Parallel vs Sequential dispatch")
    print("=" * 60)

    runner = SpecialistRunner(main_llm=None)
    tool_caller = ToolCaller(runner=runner)

    # Parallel
    req_parallel = DispatchRequest(
        user_query="Analyze this data and plan an optimization strategy",
        task_description="Analyze data and plan optimization",
        required_capabilities=["analyze", "optimize", "plan"],
        allow_parallel=True,
    )
    r_parallel = await tool_caller.dispatch(req_parallel)
    print(f"  Parallel: {r_parallel.total_specialists_used} specialists, {r_parallel.total_execution_ms:.1f}ms")

    # Sequential
    req_seq = DispatchRequest(
        user_query="First understand, then reason about this complex problem",
        task_description="Understand then reason through a problem",
        required_capabilities=["understand", "reason"],
        allow_parallel=False,
    )
    r_seq = await tool_caller.dispatch(req_seq)
    print(f"  Sequential: {r_seq.total_specialists_used} specialists, {r_seq.total_execution_ms:.1f}ms")
    print("  ✅ PASSED\n")


async def test_all_13_specialists_registered():
    print("=" * 60)
    print("TEST 4: All 13 specialists registered")
    print("=" * 60)

    all_specs = SpecialistRegistry.all()
    print(f"  Registered: {len(all_specs)} specialists")
    for s in all_specs:
        print(f"  [{s.id.value}] {s.name} ({s.param_budget}) — priority {s.priority}")
    assert len(all_specs) == 13, f"Expected 13, got {len(all_specs)}"
    print("  ✅ PASSED\n")


async def test_native_specialist_execution():
    print("=" * 60)
    print("TEST 5: Native specialist execution (NATIVE mode)")
    print("=" * 60)

    from automation_framework.mos.protocol import SpecialistTask

    runner = SpecialistRunner()
    task = SpecialistTask(
        trace_id="test-native-001",
        specialist_id="tool_caller",
        specialist_name="ToolCaller",
        sub_task="Route user query: Implement quicksort in Python",
        max_tokens=20,
    )
    res = await runner.run(task)
    print(f"  Status: {res.status}")
    print(f"  Confidence: {res.confidence}")
    print(f"  Execution: {res.execution_ms:.1f}ms")
    print(f"  Output preview: {repr(res.output[:80])}")
    assert res.confidence == 1.0, f"Expected 1.0 (NATIVE mode), got {res.confidence}"
    print("  ✅ PASSED\n")


async def main():
    print("\n[Xeren MoS] Dispatch Pipeline Smoke Test\n")
    await test_all_13_specialists_registered()
    await test_registry_lookup()
    await test_tool_caller_routing()
    await test_parallel_vs_sequential()
    await test_native_specialist_execution()
    print("[DONE] All tests passed! MoS dispatch pipeline is working.\n")
    print("Next step: train M1 checkpoint -> drop into training/checkpoints/mos/m1_understanding/")
    print("           The runner will auto-upgrade from STUB -> NATIVE.\n")


if __name__ == "__main__":
    asyncio.run(main())

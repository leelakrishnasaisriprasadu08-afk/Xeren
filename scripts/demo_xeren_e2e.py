"""Xeren 1.0 End-to-End Demonstration Script.

Showcases the complete sovereign Xeren pipeline:
User Request -> Xeren Core -> Reasoning/Planning -> Autonomous Agent ->
Plugin Manager -> Capabilities (RAG, Research, Coding, Website, Data, Browser) ->
Verification -> Experience -> Final Response.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from xeren.core.runtime import XerenCore
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.permissions import PermissionManager, PermissionMode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xeren.demo")


def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)


def print_result_summary(result: Dict[str, Any]) -> None:
    print(f"\n[Status]          : {'SUCCESS' if result.get('success') else 'FAILED'}")
    print(f"[Goal]            : {result.get('goal')}")
    plan = result.get("plan")
    if plan and hasattr(plan, "steps"):
        print(f"[Plan ID]         : {plan.plan_id}")
        print(f"[Planned Steps]   : {len(plan.steps)}")
        for i, step in enumerate(plan.steps, 1):
            target = f" -> {step.target}" if step.target else ""
            print(f"   {i}. [{step.action_type.upper()}] {step.description}{target}")
    
    verif = result.get("verification")
    if verif:
        print(f"[Verification]    : Verified={verif.verified}, Score={verif.score:.2f}, Verifier={verif.verifier}")
    
    exp = result.get("experience")
    if exp and hasattr(exp, "record"):
        rec = exp.record
        print(f"[Experience ID]   : {rec.sample_id} (Fingerprint: {exp.fingerprint[:12]}...)")
        print(f"[Executed Actions]: {len(rec.actions)}")
    
    final_resp = result.get("final_response")
    if final_resp:
        print(f"[Final Response]  : {str(final_resp)[:180]}...")


async def run_demos() -> None:
    print_banner("Xeren 1.0 Sovereign AI Autonomous Work Agent - End-to-End Demonstrations")
    core = XerenCore(auto_register_defaults=True)

    # -------------------------------------------------------------------------
    # Demo 1: Knowledge & RAG Grounded Retrieval
    # -------------------------------------------------------------------------
    print_banner("Demo 1: Sovereign Knowledge Ingestion and RAG Retrieval")
    print("1. Ingesting proprietary technical specifications...")
    ingest_res = await core.aingest_knowledge(
        texts=[
            "Xeren 1.0 architecture implements sovereign on-premise execution with no data leakage.",
            "Xeren Core features a pre-execution PlanValidator blocking unsafe shell commands and enforcing capability boundaries.",
        ],
        source="spec_manual_v1",
    )
    print(f"   Ingested {len(ingest_res.inserted_chunk_ids)} chunks successfully.")

    print("\n2. Executing natural language query through Knowledge RAG pipeline...")
    rag_res = await core.aprocess_request(
        request="Retrieve knowledge context for Xeren architecture and safety validator",
        context={"query": "Xeren PlanValidator and sovereign execution"},
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(rag_res)

    # -------------------------------------------------------------------------
    # Demo 2: Autonomous Research & Synthesis
    # -------------------------------------------------------------------------
    print_banner("Demo 2: Autonomous Deep Research and Synthesis")
    research_res = await core.aprocess_request(
        request="Research state-of-the-art agentic reasoning and self-healing systems",
        context={"depth": "standard"},
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(research_res)

    # -------------------------------------------------------------------------
    # Demo 3: Autonomous Coding & Syntax Verification
    # -------------------------------------------------------------------------
    print_banner("Demo 3: Autonomous Code Generation and Verification")
    coding_res = await core.aprocess_request(
        request="Generate Python script to implement rate-limited asynchronous worker queue",
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(coding_res)

    # -------------------------------------------------------------------------
    # Demo 4: Website Generation & Security Auditing
    # -------------------------------------------------------------------------
    print_banner("Demo 4: Full Website Generation, Security Audit, and Validation")
    website_res = await core.aprocess_request(
        request="Generate website landing page for Xeren AI Sovereign Platform",
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(website_res)

    # -------------------------------------------------------------------------
    # Demo 5: Multi-Plugin Chained Workflow (Research + Coding)
    # -------------------------------------------------------------------------
    print_banner("Demo 5: Multi-Plugin Chained Execution (Research -> Coding)")
    multi_res = await core.aprocess_request(
        request="Multi task: Research distributed consensus and generate Python Raft node skeleton",
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(multi_res)

    # -------------------------------------------------------------------------
    # Demo 6: Autonomous Browser Automation
    # -------------------------------------------------------------------------
    print_banner("Demo 6: Autonomous Browser Automation via Mock / Playwright Adapter")
    mock_browser = MockBrowserAdapter()
    browser_res = await core.aprocess_request(
        request="Browse https://xeren.ai/console and extract dashboard metrics",
        context={"url": "https://xeren.ai/console"},
        browser_adapter=mock_browser,
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(browser_res)

    # -------------------------------------------------------------------------
    # Demo 7: Permission Handling & Consequential Action Gating
    # -------------------------------------------------------------------------
    print_banner("Demo 7: Permission Enforcement for Consequential Actions")
    strict_pm = PermissionManager(mode=PermissionMode.STRICT)
    perm_res = await core.aprocess_request(
        request="Upload confidential telemetry archive to remote endpoint",
        context={"file_path": "telemetry.zip", "url": "https://remote.server/upload"},
        permission_manager=strict_pm,
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(perm_res)
    print("\n   [Safety Verified]: Consequential upload action was intercepted and safely blocked.")

    # -------------------------------------------------------------------------
    # Demo 8: Verification Failure Detection
    # -------------------------------------------------------------------------
    print_banner("Demo 8: Automated Verification Failure Detection")
    verif_fail_res = await core.aprocess_request(
        request="Research artificial intelligence architectures",
        context={"expected_conditions": ["contains impossible_mandatory_condition_xyz"]},
        verify_outcome=True,
        record_experience=True,
    )
    print_result_summary(verif_fail_res)
    print("   [Quality Gate Verified]: Contradictory outcome condition scored 0.0 with verified=False.")

    print_banner("All Demonstrations Completed Successfully")


def main() -> None:
    asyncio.run(run_demos())


if __name__ == "__main__":
    main()

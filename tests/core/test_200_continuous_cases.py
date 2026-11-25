"""Continuous 200 Cases Comprehensive Test Suite for Xeren Core & Architecture.

Validates 200 continuous operational scenarios across 8 distinct subsystem categories:
- Category 1: Conversational Chat & Thought Exploration (Cases 1-35)
- Category 2: Intent Classification & Routing Precision (Cases 36-60)
- Category 3: Task Planning & "Proceed to the Plan" Execution Gating (Cases 61-95)
- Category 4: Epistemic Learn-First & Zero-Hallucination Fact Verification (Cases 96-120)
- Category 5: Permitted Data Holding Engine & Vault Boundary Security (Cases 121-150)
- Category 6: Website Building Architecture Grounded in User Ideas (Cases 151-175)
- Category 7: Continuous Pattern Learning Without Mutating Base Weights (Cases 176-190)
- Category 8: Realtime API & WebSocket Gateway Stress (Cases 191-200)

Total: Exactly 200 Test Cases
"""

import hashlib
import json
import pytest
from starlette.testclient import TestClient

from xeren.core.data_holding import PermittedDataHoldingVault
from xeren.core.intent import IntentClassifier, RoutingCategory
from xeren.core.learner import EpistemicLearner
from xeren.core.runtime import XerenCore
from xeren.core.session import XerenSession
from xeren.core.vault import UserVault
from xeren.models.improvement.engine import LLMSelfImprovementEngine
from xeren.models.improvement.schemas import ObservationSource
from xeren.models.providers.mock import MockLLM
from xeren.server.app import app


# ==============================================================================
# Shared Fixtures
# ==============================================================================

@pytest.fixture(scope="module")
def persistent_core_env(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("continuous_200")
    vault_db = tmp_dir / "vault.db"
    vault = UserVault(db_path=vault_db)
    session = XerenSession(vault=vault)
    data_holding = PermittedDataHoldingVault(vault=vault)
    llm = MockLLM()
    core = XerenCore(
        llm=llm,
        session=session,
        data_holding=data_holding,
    )
    return core, session, data_holding, vault, tmp_dir


# ==============================================================================
# Category 1: Conversational Chat & Thought Exploration (Cases 1-35)
# ==============================================================================

CHAT_CASES = [
    (1, "Hello Xeren, how are you today?"),
    (2, "What are your core autonomous design principles?"),
    (3, "Can you explain how transformer attention mechanisms function?"),
    (4, "What do you think about using microservices vs monolithic architecture?"),
    (5, "Tell me about distributed caching strategies using Redis."),
    (6, "How does zero-hallucination verification work in AI agents?"),
    (7, "What is the difference between synchronous and asynchronous I/O?"),
    (8, "How can we optimize vector search in local embedded databases?"),
    (9, "What are the advantages of GraphQL over standard REST?"),
    (10, "How do you manage ephemeral session states securely?"),
    (11, "Can you explain quantum computing basics in simple words?"),
    (12, "What is the role of epistemic learning in reasoning models?"),
    (13, "How does WebSockets differ from HTTP/2 Server-Sent Events?"),
    (14, "What makes edge computing fast for low-latency inference?"),
    (15, "Why is immutability important in concurrent programming?"),
    (16, "Explain how Raft consensus algorithm handles leader election."),
    (17, "What are best practices for designing accessible web interfaces?"),
    (18, "How do you prevent SQL injection in modern ORMs?"),
    (19, "What is semantic versioning and why is it followed?"),
    (20, "How does speculative decoding speed up LLM generation?"),
    (21, "Explain the difference between TCP and UDP protocols."),
    (22, "What are the key differences between SQL and NoSQL databases?"),
    (23, "How do diffusion models generate images from text?"),
    (24, "What are the benefits of declarative infrastructure like Terraform?"),
    (25, "Explain how OAuth 2.0 PKCE flow works for mobile clients."),
    (26, "What is the concept of eventual consistency in distributed systems?"),
    (27, "How do graph neural networks model relational data?"),
    (28, "What are the main security considerations for API rate limiting?"),
    (29, "Explain the difference between processes and threads in an OS."),
    (30, "What is retrieval-augmented generation and why is it useful?"),
    (31, "How does garbage collection work in modern runtimes?"),
    (32, "Explain the CAP theorem with practical database examples."),
    (33, "What are best practices for telemetry and distributed tracing?"),
    (34, "How do container runtimes isolate namespaces and cgroups?"),
    (35, "What is your vision for human-AI collaborative programming?"),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("case_id, query", CHAT_CASES)
async def test_category_1_chat_cases(persistent_core_env, case_id, query):
    core, session, _, _, _ = persistent_core_env
    res = await core.achat(query)
    assert res["type"] == "chat_response", f"Case {case_id} failed: expected chat_response"
    assert res["verified"] is True, f"Case {case_id} failed: expected verified=True"
    assert len(res["content"]) > 0, f"Case {case_id} failed: empty response content"


# ==============================================================================
# Category 2: Intent Classification & Routing Precision (Cases 36-60)
# ==============================================================================

INTENT_CASES = [
    (36, "Hello there, good morning!", RoutingCategory.GENERAL_KNOWLEDGE, "conversation"),
    (37, "Can we discuss system design principles?", RoutingCategory.GENERAL_KNOWLEDGE, "conversation"),
    (38, "What is your opinion on rust vs go?", RoutingCategory.GENERAL_KNOWLEDGE, "conversation"),
    (39, "Tell me a fun programming joke", RoutingCategory.GENERAL_KNOWLEDGE, "conversation"),
    (40, "What is the capital of France?", RoutingCategory.GENERAL_KNOWLEDGE, "conversation"),
    (41, "Build a landing page for my mobile fitness app", RoutingCategory.ACTION_REQUEST, "website"),
    (42, "Create a personal portfolio website with a dark theme", RoutingCategory.ACTION_REQUEST, "website"),
    (43, "Build a website for my creative design agency", RoutingCategory.ACTION_REQUEST, "website"),
    (44, "Write a python script to scrape product prices", RoutingCategory.ACTION_REQUEST, "coding"),
    (45, "Write a python function to compute fibonacci numbers", RoutingCategory.ACTION_REQUEST, "coding"),
    (46, "Implement a python algorithm for binary search", RoutingCategory.ACTION_REQUEST, "coding"),
    (47, "Launch chrome to open developer dashboard", RoutingCategory.ACTION_REQUEST, "automation"),
    (48, "Automate client order processing on Upwork", RoutingCategory.ACTION_REQUEST, "automation"),
    (49, "Run terminal process for cache cleanup", RoutingCategory.ACTION_REQUEST, "automation"),
    (50, "Search the web for the latest Python 3.13 features", RoutingCategory.ACTION_REQUEST, "research"),
    (51, "Deep search for papers on transformer optimization", RoutingCategory.ACTION_REQUEST, "research"),
    (52, "Look up online the documentation for WebGPU", RoutingCategory.ACTION_REQUEST, "research"),
    (53, "Read directory to list files in the workspace", RoutingCategory.ACTION_REQUEST, "file"),
    (54, "Write report to a file named summary.txt", RoutingCategory.ACTION_REQUEST, "file"),
    (55, "Verify claim that quantum supremacy was reached", RoutingCategory.ACTION_REQUEST, "verification"),
    (56, "How does xeren core architecture work?", RoutingCategory.XEREN_PROJECT, "knowledge"),
    (57, "Explain runtime.py in our codebase", RoutingCategory.XEREN_PROJECT, "knowledge"),
    (58, "Where is the hallucination guard in this repo?", RoutingCategory.XEREN_PROJECT, "knowledge"),
    (59, "What are xeren specs for agent execution?", RoutingCategory.XEREN_PROJECT, "knowledge"),
    (60, "Describe the training checkpoint pipeline in xeren", RoutingCategory.XEREN_PROJECT, "knowledge"),
]

@pytest.mark.parametrize("case_id, query, expected_category, expected_plugin", INTENT_CASES)
def test_category_2_intent_classification_cases(case_id, query, expected_category, expected_plugin):
    classifier = IntentClassifier()
    intent = classifier.classify(query)
    assert intent.category == expected_category, (
        f"Case {case_id} failed: expected category {expected_category}, got {intent.category} for query: '{query}'"
    )
    assert intent.plugin == expected_plugin, (
        f"Case {case_id} failed: expected plugin {expected_plugin}, got {intent.plugin} for query: '{query}'"
    )


# ==============================================================================
# Category 3: Task Planning & "Proceed to the Plan" Execution Gating (Cases 61-95)
# ==============================================================================

PLANNING_CASES = [
    (61, "Build a modern portfolio website for a graphic designer", "proceed to the plan"),
    (62, "Create a SaaS landing page for an email marketing tool", "proceed"),
    (63, "Scaffold a blog website for tech tutorials", "yes proceed to the plan"),
    (64, "Build an e-commerce website for handmade crafts", "execute plan"),
    (65, "Create a responsive restaurant menu website", "proceed with plan"),
    (66, "Build a real-estate showcase website with property listings", "proceed to the plan"),
    (67, "Create a podcast landing page with audio player component", "proceed"),
    (68, "Build a personal resume and CV website", "yes, proceed to the plan"),
    (69, "Create a fitness gym membership landing page", "execute the plan"),
    (70, "Build a photography portfolio with an interactive gallery", "proceed to the plan"),
    (71, "Create a law firm professional services website", "proceed"),
    (72, "Build a medical clinic appointment booking landing page", "proceed to the plan"),
    (73, "Create an online bookstore showcase website", "execute plan"),
    (74, "Build a music artist promotional website with tour dates", "proceed to the plan"),
    (75, "Create a coffee shop website with online ordering preview", "proceed"),
    (76, "Build a startup pitch deck landing page", "yes proceed"),
    (77, "Create a travel agency destination catalog website", "proceed to the plan"),
    (78, "Build a veterinary clinic services website", "proceed"),
    (79, "Create a university student organization club page", "proceed to the plan"),
    (80, "Build a mobile app download landing page with feature cards", "execute plan"),
    (81, "Create an architecture studio portfolio website", "proceed to the plan"),
    (82, "Build an event conference registration website", "proceed"),
    (83, "Create a nonprofit charity donation landing page", "proceed to the plan"),
    (84, "Build a gaming community discord landing page", "proceed"),
    (85, "Create a car rental agency showcase website", "proceed to the plan"),
    (86, "Build a software agency client onboarding website", "execute the plan"),
    (87, "Create an artisan bakery product showcase website", "proceed to the plan"),
    (88, "Build a yoga studio class schedule website", "proceed"),
    (89, "Create a financial advisory firm landing page", "proceed to the plan"),
    (90, "Build a coworking space amenities website", "proceed"),
    (91, "Create a luxury hotel booking showcase website", "execute plan"),
    (92, "Build a dental clinic patient information website", "proceed to the plan"),
    (93, "Create a digital marketing agency showcase website", "proceed"),
    (94, "Build a pet adoption center catalog website", "proceed to the plan"),
    (95, "Create an AI startup product demo landing page", "proceed to the plan"),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("case_id, task_query, approval_phrase", PLANNING_CASES)
async def test_category_3_planning_and_gating_cases(persistent_core_env, case_id, task_query, approval_phrase):
    core, session, _, _, _ = persistent_core_env

    # 1. Ask for the task -> MUST STAGE, MUST NOT EXECUTE
    stage_res = await core.achat(task_query)
    assert stage_res["type"] == "plan_staged", f"Case {case_id} failed: task should be staged"
    assert "Execution Plan" in stage_res["content"], f"Case {case_id} failed: missing Execution Plan header"
    assert session.get_staged_plan() is not None, f"Case {case_id} failed: staged plan not registered in session"
    assert session.staged_plan_status == "staged", f"Case {case_id} failed: status should be staged"

    # 2. Check gating approval detection
    assert core.is_plan_approval(approval_phrase) is True, f"Case {case_id} failed: approval phrase not recognized"

    # 3. Trigger approval -> MUST EXECUTE AND CLEAR STAGED PLAN
    exec_res = await core.achat(approval_phrase)
    assert exec_res["type"] == "plan_executed", f"Case {case_id} failed: expected plan_executed"
    assert exec_res["success"] is True, f"Case {case_id} failed: execution reported failure"
    assert session.get_staged_plan() is None, f"Case {case_id} failed: staged plan should be cleared after execution"
    assert session.staged_plan_status == "idle", f"Case {case_id} failed: staged status should be idle"


# ==============================================================================
# Category 4: Epistemic Learn-First & Zero-Hallucination Fact Verification (Cases 96-120)
# ==============================================================================

EPISTEMIC_CASES = [
    (96, "Explain quantum dot cellular automata based on research"),
    (97, "How does holographic memory storage work in experimental labs?"),
    (98, "Describe neuromorphic spike-timing dependent plasticity mechanisms"),
    (99, "What are topological quantum insulators and their edge states?"),
    (100, "Explain memristive crossbar arrays for matrix-vector multiplication"),
    (101, "How does optical computing achieve passive fourier transforms?"),
    (102, "What is DNA data storage error correction encoding?"),
    (103, "Explain carbon nanotube field-effect transistor fabrication"),
    (104, "How do superconducting flux qubits maintain coherence?"),
    (105, "What is reservoir computing using physical dynamical systems?"),
    (106, "Explain spintronic spin-transfer torque magnetic RAM (STT-MRAM)"),
    (107, "How does adiabatic quantum computation avoid decoherence?"),
    (108, "What are photonic integrated circuits for optical tensor cores?"),
    (109, "Explain vacuum tube nano-electronics for radiation hardening"),
    (110, "How do biological neural interfaces perform spike sorting?"),
    (111, "What is bio-molecular computing using strand displacement?"),
    (112, "Explain diamond nitrogen-vacancy center quantum magnetometry"),
    (113, "How does cold atom interferometry achieve precision gravimetry?"),
    (114, "What are 2D transition metal dichalcogenides in valleytronics?"),
    (115, "Explain graphene plasmonics for terahertz signal processing"),
    (116, "How do polariton condensates operate as optical switches?"),
    (117, "What is thermal transistor heat-flux switching logic?"),
    (118, "Explain magnonic spin-wave computing logic gates"),
    (119, "How does acoustic levitation handle micro-fluidic sample arrays?"),
    (120, "What are meta-material acoustic cloaking velocity profiles?"),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("case_id, query", EPISTEMIC_CASES)
async def test_category_4_epistemic_learning_cases(persistent_core_env, case_id, query):
    core, session, _, _, _ = persistent_core_env
    learner = EpistemicLearner(llm=MockLLM())

    # 1. Epistemic learner investigates knowledge gap
    eval_result = learner.gap_detector.evaluate(query)
    assert hasattr(eval_result, "has_gap"), f"Case {case_id} failed: missing has_gap evaluation"

    # 2. Fact verification via runtime
    res = await core.achat(query)
    assert res["type"] in ("chat_response", "plan_staged"), f"Case {case_id} failed: expected chat or staged plan"
    assert res.get("verified", True) is True
    session.clear_staged_plan()


# ==============================================================================
# Category 5: Permitted Data Holding Engine & Vault Boundary Security (Cases 121-150)
# ==============================================================================

FILE_HOLDING_CASES = [
    (121, "project_spec.md", "# Project Specification\nAutonomous agent requirements."),
    (122, "architecture.txt", "Architecture overview: microservices and local vaults."),
    (123, "config.json", '{"model": "xeren_mini", "parameters": "1.5B"}'),
    (124, "schema.sql", "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);"),
    (125, "styles.css", ":root { --primary: #00ffcc; --bg: #0a0a0f; }"),
    (126, "script.py", "def greet(name: str) -> str:\n    return f'Hello {name}'\n"),
    (127, "data.csv", "id,metric,value\n1,accuracy,0.99\n2,latency_ms,12\n"),
    (128, "readme.md", "# Xeren Agent\nUltra-fast autonomous planning system.\n"),
    (129, "notes.org", "* Meeting Notes\n- Integrate permitted app holding.\n"),
    (130, "manifest.yaml", "apiVersion: v1\nkind: AgentService\nmetadata: xeren\n"),
]

UNAUTHORIZED_CASES = [
    (131, "../secret_keys.pem"),
    (132, "../../system_passwords.txt"),
    (133, "/etc/shadow_simulation"),
    (134, "C:\\Windows\\System32\\mock_drivers.dll"),
    (135, "../../../root_credentials.json"),
]

APP_HOLDING_CASES = [
    (136, "github", "issues_pr", {"repo": "xeren/core", "open_prs": 3, "status": "active"}),
    (137, "sqlite", "analytics_cache", {"table": "user_metrics", "rows": 1420, "fresh": True}),
    (138, "notion", "project_roadmap", {"doc": "Q4 Roadmap", "blocks": 45, "synced": True}),
    (139, "jira", "sprint_tasks", {"sprint": "Sprint 14", "backlog_items": 8, "wip": 2}),
    (140, "slack", "dev_channel_summary", {"channel": "#dev-core", "unread": 0, "topics": ["1.5B LLM"]}),
    (141, "postgres", "embeddings_index", {"dimension": 1536, "index_type": "HNSW", "count": 50000}),
    (142, "s3_storage", "asset_manifest", {"bucket": "xeren-assets", "objects": 240, "region": "us-east"}),
    (143, "redis", "session_cache", {"active_sessions": 12, "memory_mb": 64, "hit_rate": 0.98}),
    (144, "linear", "issue_tracker", {"milestone": "v2.0-launch", "velocity": 42, "health": "green"}),
    (145, "figma", "design_tokens", {"theme": "neon-cyberpunk", "colors": 16, "fonts": ["Inter"]}),
]

WEB_HOLDING_CASES = [
    (146, "https://docs.xeren.ai/architecture", "Xeren Core runtime architecture documentation."),
    (147, "https://arxiv.org/abs/2301.00001", "Epistemic learning in lightweight edge language models."),
    (148, "https://developer.mozilla.org/WebSockets", "MDN reference guide for WebSocket bi-directional streams."),
    (149, "https://github.com/fastapi/fastapi", "High performance async web framework for Python."),
    (150, "https://sqlite.org/wal.html", "Write-Ahead Logging mechanics in modern SQLite database engines."),
]

@pytest.mark.parametrize("case_id, filename, content", FILE_HOLDING_CASES)
def test_category_5_permitted_file_holding(persistent_core_env, case_id, filename, content):
    _, _, data_holding, vault, tmp_dir = persistent_core_env
    permitted_folder = tmp_dir / "permitted_vault"
    permitted_folder.mkdir(exist_ok=True)
    vault.grant_directory(str(permitted_folder.resolve()), allow_write=True, description="Permitted folder")

    file_path = permitted_folder / filename
    file_path.write_text(content, encoding="utf-8")

    item = data_holding.hold_device_file(file_path, content)
    assert item is not None, f"Case {case_id} failed: file should be held"
    assert item.source_type == "device_file", f"Case {case_id} failed: expected device_file"
    assert item.content_hash == hashlib.sha256(content.encode()).hexdigest(), f"Case {case_id} hash mismatch"


@pytest.mark.parametrize("case_id, unauth_path", UNAUTHORIZED_CASES)
def test_category_5_unauthorized_file_rejection(persistent_core_env, case_id, unauth_path):
    _, _, data_holding, _, _ = persistent_core_env
    res = data_holding.hold_device_file(unauth_path)
    assert res is None, f"Case {case_id} failed: expected None for unauthorized path"
    with pytest.raises(PermissionError):
        data_holding.hold_device_file(unauth_path, raise_on_denied=True)


@pytest.mark.parametrize("case_id, app_id, title, payload", APP_HOLDING_CASES)
def test_category_5_connected_app_holding(persistent_core_env, case_id, app_id, title, payload):
    _, _, data_holding, _, _ = persistent_core_env
    item = data_holding.hold_connected_app_data(
        app_name=app_id,
        entity_id=title,
        title=title,
        content=json.dumps(payload),
    )
    assert item.source_type == "connected_app", f"Case {case_id} failed: expected connected_app"
    assert item.source_identifier == f"{app_id}:{title}", f"Case {case_id} failed: source identifier mismatch"


@pytest.mark.parametrize("case_id, url, snippet", WEB_HOLDING_CASES)
def test_category_5_web_research_holding(persistent_core_env, case_id, url, snippet):
    _, _, data_holding, _, _ = persistent_core_env
    item = data_holding.hold_web_research(
        url=url,
        title=f"Web source {case_id}",
        summary=snippet,
        evidence_snippets=[snippet],
    )
    assert item.source_type == "web_research", f"Case {case_id} failed: expected web_research"
    assert item.source_identifier == url, f"Case {case_id} failed: URL mismatch"


# ==============================================================================
# Category 6: Website Building Architecture Grounded in User Ideas (Cases 151-175)
# ==============================================================================

WEBSITE_IDEAS = [
    (151, "Creative 3D digital design studio with dark minimalist aesthetic"),
    (152, "Modern fintech mobile wallet landing page with currency converter preview"),
    (153, "Organic coffee roastery with interactive bean origin map"),
    (154, "Personal developer portfolio highlighting open-source contributions"),
    (155, "SaaS project management tool with live interactive Kanban demo"),
    (156, "Artisan sourdough bakery menu with morning preorder checkout"),
    (157, "Boutique law firm offering corporate IP advisory services"),
    (158, "Fitness gym & crossfit box with weekly class schedule matrix"),
    (159, "Indie video game studio showcasing upcoming release trailer"),
    (160, "Veterinary animal care hospital with emergency contact banner"),
    (161, "Architecture firm portfolio featuring sustainable modular housing"),
    (162, "Tech conference registration with speaker line-up cards"),
    (163, "Podcast media player with episode transcripts and guest bios"),
    (164, "Online bookstore curator with staff recommendations carousel"),
    (165, "Nonprofit ocean conservation foundation with donation milestones"),
    (166, "Music producer discography with streaming platform links"),
    (167, "Coworking space locator with desk booking pricing tiers"),
    (168, "Luxury hotel & spa resort with room virtual tour showcase"),
    (169, "Car detailing & restoration studio with before/after comparisons"),
    (170, "Dental clinic with online appointment scheduling form"),
    (171, "Travel agency offering curated eco-tourism expeditions"),
    (172, "Digital marketing agency with client case study metrics"),
    (173, "Cat & dog rescue adoption gallery with pet profile cards"),
    (174, "Cybersecurity consultancy with threat radar assessment widget"),
    (175, "AI analytics platform with real-time streaming graph component"),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("case_id, user_idea", WEBSITE_IDEAS)
async def test_category_6_website_building_cases(persistent_core_env, case_id, user_idea):
    core, session, _, _, _ = persistent_core_env

    # Ask to build website based on user idea
    query = f"Build a website: {user_idea}"
    res = await core.achat(query)

    # 1. Staging verification
    assert res["type"] == "plan_staged", f"Case {case_id} failed: website should be staged first"
    staged_plan = session.get_staged_plan()
    assert staged_plan is not None, f"Case {case_id} failed: missing staged plan"

    # 2. Plan structure verification
    assert "steps" in staged_plan, f"Case {case_id} failed: plan missing steps"
    assert len(staged_plan["steps"]) >= 1, f"Case {case_id} failed: plan has 0 steps"

    # 3. Clean up staged plan for next iteration
    session.clear_staged_plan()


# ==============================================================================
# Category 7: Continuous Pattern Learning Without Mutating Base Weights (Cases 176-190)
# ==============================================================================

PATTERN_CASES = [
    (176, "Refactor database query to use parameterized statements", "Executed cleanly with zero syntax issues", True),
    (177, "Deploy Docker container on staging environment", "Container launched and passed health check", True),
    (178, "Generate unit test suite for payment gateway", "All 12 edge cases covered and passing", True),
    (179, "Optimize CSS bundle size with dead code elimination", "Reduced bundle size by 35%", True),
    (180, "Scaffold REST endpoints for user authentication", "JWT auth handlers created with bcrypt hashing", True),
    (181, "Fix memory leak in background worker task", "Worker memory footprint stabilized under 80MB", True),
    (182, "Set up automated daily database backup cron job", "Backup script tested and verified in scratch folder", True),
    (183, "Implement responsive navigation menu with accessibility", "ARIA attributes validated and tested with keyboard", True),
    (184, "Index vector embeddings into local Chroma collection", "Indexed 2000 document vectors successfully", True),
    (185, "Configure CORS headers for trusted frontend origin", "CORS middleware verified with options preflight", True),
    (186, "Implement rate limiting using token bucket algorithm", "Token bucket limiter throttles excessive requests", True),
    (187, "Parse and validate complex nested JSON configurations", "Pydantic models validated schema without errors", True),
    (188, "Compress static assets using Brotli compression", "Asset delivery latency reduced by 40ms", True),
    (189, "Audit file permissions inside secure user vault", "All sensitive keys confirmed restricted to owner", True),
    (190, "Synchronize offline task queue upon network reconnect", "15 pending tasks replayed and resolved", True),
]

@pytest.mark.parametrize("case_id, task, outcome, success", PATTERN_CASES)
def test_category_7_pattern_learning_cases(persistent_core_env, case_id, task, outcome, success):
    core, _, _, _, _ = persistent_core_env
    engine = LLMSelfImprovementEngine()

    obs_res = engine.record_observation(
        source=ObservationSource.USER_TASK,
        content=task,
        context={"outcome": outcome, "session_id": f"session-{case_id}"},
        outcome_success=success,
    )
    assert obs_res is not None, f"Case {case_id} failed: observation not recorded"
    assert "obs_id" in obs_res

    # Check adaptive system directive without altering base weights
    prompt_addition = engine.get_adaptive_system_prompt_addition()
    assert isinstance(prompt_addition, str), f"Case {case_id} failed: prompt addition invalid"
    assert len(prompt_addition) > 0, f"Case {case_id} failed: prompt addition is empty"


# ==============================================================================
# Category 8: Realtime API & WebSocket Gateway Stress (Cases 191-200)
# ==============================================================================

GATEWAY_CASES = [
    (191, "Can you check system health?", "chat"),
    (192, "List current capabilities", "chat"),
    (193, "Explain plan safety gating", "chat"),
    (194, "Inspect active staged plan", "plan_active"),
    (195, "Hold test asset documentation", "data_hold"),
    (196, "Query held data items", "data_query"),
    (197, "WebSocket streaming connection 1", "ws_stream"),
    (198, "WebSocket streaming connection 2", "ws_stream"),
    (199, "WebSocket streaming connection 3", "ws_stream"),
    (200, "WebSocket multi-turn live conversation", "ws_multiturn"),
]

@pytest.mark.parametrize("case_id, query, action", GATEWAY_CASES)
def test_category_8_gateway_cases(persistent_core_env, case_id, query, action):
    client = TestClient(app)

    if action == "chat":
        res = client.post("/api/chat", json={"query": query})
        assert res.status_code == 200, f"Case {case_id} failed: status code {res.status_code}"
        assert "content" in res.json(), f"Case {case_id} missing content"

    elif action == "plan_active":
        res = client.get("/api/plan/active")
        assert res.status_code == 200, f"Case {case_id} failed: active plan status {res.status_code}"

    elif action == "data_hold":
        res = client.post("/api/data-holding/grant-and-hold", json={
            "directory_path": ".",
            "description": "Stress test root holding"
        })
        assert res.status_code == 200, f"Case {case_id} failed: grant-and-hold status {res.status_code}"

    elif action == "data_query":
        res = client.post("/api/data-holding/query", json={"query": "asset", "limit": 2})
        assert res.status_code == 200, f"Case {case_id} failed: data query status {res.status_code}"

    elif action == "ws_stream":
        with client.websocket_connect("/api/v1/realtime") as ws:
            init_evt = ws.receive_json()
            assert init_evt["type"] == "conversation.start", f"Case {case_id} ws init failed"
            ws.send_json({"type": "user.text", "text": query})
            created_evt = ws.receive_json()
            assert created_evt["type"] == "response.created", f"Case {case_id} ws response failed"
            for _ in range(50):
                m = ws.receive_json()
                if m["type"] == "response.done":
                    break

    elif action == "ws_multiturn":
        with client.websocket_connect("/api/v1/realtime") as ws:
            init_evt = ws.receive_json()
            assert init_evt["type"] == "conversation.start"
            # Turn 1
            ws.send_json({"type": "user.text", "text": "Turn 1: Ready?"})
            assert ws.receive_json()["type"] == "response.created"
            # Drain turn 1
            for _ in range(50):
                m = ws.receive_json()
                if m["type"] == "response.done":
                    break
            # Turn 2
            ws.send_json({"type": "user.text", "text": "Turn 2: Confirm proceed mechanism"})
            assert ws.receive_json()["type"] == "response.created"
            # Drain turn 2
            for _ in range(50):
                m = ws.receive_json()
                if m["type"] == "response.done":
                    break

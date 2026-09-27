# Xeren Workspace Architecture & Directory Guide

This document defines the clear 3-part division of the Xeren repository:
1. **Frontend** — Modern Web Interface (React, Vite, TypeScript, Tailwind)
2. **Backend** — FastAPI Application, Agent Engine, and Automation Framework
3. **Others** — Machine Learning Training (MoS), Automation Scripts, Tests, Data, and Documentation

---

## 🌐 1. Frontend (`frontend/`)

The user-facing workstation interface for interacting with Xeren, managing projects, viewing agent reasoning traces, and triggering automation tasks.

| Path | Purpose |
|---|---|
| [`frontend/src/`](file:///c:/Users/leela/Dropbox/Xeren/frontend/src) | Main React TypeScript source code |
| [`frontend/src/components/`](file:///c:/Users/leela/Dropbox/Xeren/frontend/src/components) | UI components (chat, agent traces, settings, sidebar, layouts) |
| [`frontend/src/pages/`](file:///c:/Users/leela/Dropbox/Xeren/frontend/src/pages) | Route views (Chat, Projects, Workflow Studio, History) |
| [`frontend/src/services/`](file:///c:/Users/leela/Dropbox/Xeren/frontend/src/services) | API clients connecting to the FastAPI backend (`http://127.0.0.1:8000`) |
| [`frontend/src/styles/`](file:///c:/Users/leela/Dropbox/Xeren/frontend/src/styles) | Tailwind CSS tokens, theme definitions (dark/light mode) |
| [`frontend/package.json`](file:///c:/Users/leela/Dropbox/Xeren/frontend/package.json) | Frontend dependencies and build scripts (`vite`, `lucide-react`, `tailwind`) |
| [`frontend/vite.config.ts`](file:///c:/Users/leela/Dropbox/Xeren/frontend/vite.config.ts) | Vite bundling and dev proxy configuration |

**How to run Frontend:**
```bash
npm run dev
# or
npm run dev --prefix frontend
```

---

## ⚙️ 2. Backend (`backend/`)

The core intelligence, agent runtime, execution sandbox, and API server.

### A. Core Backend Application (`backend/src/xeren/`)
| Path | Purpose |
|---|---|
| [`backend/src/xeren/server/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/server) | FastAPI application entry point (`app.py`), WebSocket handlers, and route definitions |
| [`backend/src/xeren/agent/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/agent) | Autonomous loop, task decomposition, memory retrieval, tool dispatching |
| [`backend/src/xeren/automation/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/automation) | Browser automation (Playwright), GUI automation, filesystem tools |
| [`backend/src/xeren/models/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/models) | Model abstraction layer (`create_llm`), provider interfaces, tokenizers |
| [`backend/src/xeren/db/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/db) | SQLModel/PostgreSQL/SQLite database models, migrations, and session management |
| [`backend/src/xeren/rag/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/rag) | Retrieval-Augmented Generation, vector embeddings, document indexing |
| [`backend/src/xeren/mcp/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/mcp) | Model Context Protocol servers and client tool bridges |
| [`backend/src/xeren/auth/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/auth) | Authentication, JWT sessions, security validation |
| [`backend/src/xeren/voice/`](file:///c:/Users/leela/Dropbox/Xeren/backend/src/xeren/voice) | Real-time speech-to-text (STT) and text-to-speech (TTS) pipelines |

### B. Automation & Mixture of Specialists Framework (`backend/automation_framework/`)
| Path | Purpose |
|---|---|
| [`backend/automation_framework/mos/`](file:///c:/Users/leela/Dropbox/Xeren/backend/automation_framework/mos) | **Mixture of Specialists (MoS)** layer: orchestrator, tool caller, specialist registry, protocol, runner |
| [`backend/automation_framework/core/`](file:///c:/Users/leela/Dropbox/Xeren/backend/automation_framework/core) | Shared LLM client bridge, base automation interfaces |
| [`backend/automation_framework/plugins/`](file:///c:/Users/leela/Dropbox/Xeren/backend/automation_framework/plugins) | Modular automation plugins (web scrapers, data handlers, dev tools) |
| [`backend/automation_framework/tools/`](file:///c:/Users/leela/Dropbox/Xeren/backend/automation_framework/tools) | Tool execution engines (terminal, browser, code sandbox) |

**How to run Backend:**
```bash
npm run backend
# or
powershell -ExecutionPolicy Bypass -File ./scripts/start_backend.ps1
```

---

## 🔬 3. Others (Training, Scripts, Data, Tests, Docs)

Supporting systems responsible for custom model training, deployment utilities, test suites, and project assets.

### A. Neural Model Training (`training/`)
Dedicated environment for developing, pre-training, fine-tuning, and testing native Xeren neural weights.
* **Architecture**: 100% native PyTorch `XerenTransformer` with RMSNorm, RoPE, SwiGLU, GQA, and SDPA.
* **Tokenizer**: Native 32,768 vocabulary custom Byte-Pair Encoding (`XerenTokenizer`).
* **Checkpoints**: [`training/checkpoints/`](file:///c:/Users/leela/Dropbox/Xeren/training/checkpoints) (Stage 1 base, Orchestrator v2, MoS ToolCaller).
* **Scripts**:
  * [`training/scripts/train_main_orchestrator.py`](file:///c:/Users/leela/Dropbox/Xeren/training/scripts/train_main_orchestrator.py) — Main model continuation training.
  * [`training/scripts/train_tool_caller.py`](file:///c:/Users/leela/Dropbox/Xeren/training/scripts/train_tool_caller.py) — Neural tool caller and routing trainer.
  * [`training/scripts/build_main_orchestrator_dataset.py`](file:///c:/Users/leela/Dropbox/Xeren/training/scripts/build_main_orchestrator_dataset.py) — Orchestrator dataset generator.
  * [`training/scripts/build_tool_caller_dataset.py`](file:///c:/Users/leela/Dropbox/Xeren/training/scripts/build_tool_caller_dataset.py) — ToolCaller dataset generator.

### B. Automation & Operational Scripts (`scripts/`)
| Script | Description |
|---|---|
| [`scripts/start_backend.ps1`](file:///c:/Users/leela/Dropbox/Xeren/scripts/start_backend.ps1) | Starts the FastAPI server on port 8000 with process cleanup |
| [`scripts/talk_to_xeren.ps1`](file:///c:/Users/leela/Dropbox/Xeren/scripts/talk_to_xeren.ps1) | Interactive CLI terminal to chat directly with Xeren |
| [`scripts/chat_agent.py`](file:///c:/Users/leela/Dropbox/Xeren/scripts/chat_agent.py) | CLI agent conversation runner |
| [`scripts/demo_xeren_e2e.py`](file:///c:/Users/leela/Dropbox/Xeren/scripts/demo_xeren_e2e.py) | Full end-to-end integration demo |

### C. Testing Suites (`tests/`)
* Unit tests, integration tests, and Playwright browser automation tests.
* Tested with `pytest` (`python -m pytest tests`).

### D. Documentation & Runtime Data (`docs/` & `data/`)
* [`docs/`](file:///c:/Users/leela/Dropbox/Xeren/docs): Architecture specifications, data pipelines, system designs.
* [`data/`](file:///c:/Users/leela/Dropbox/Xeren/data): Local vector databases (ChromaDB), SQLite state, downloaded knowledge assets.
* [`workspace/`](file:///c:/Users/leela/Dropbox/Xeren/workspace): Sandboxed environment for Xeren agent code generation and file operations.

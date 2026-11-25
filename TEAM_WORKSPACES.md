# 👥 Xeren — Team Collaboration & Work Partitioning Matrix

This document defines the **5 Independent Engineering Separation Areas** for the Xeren team. Each team member or sub-team can work simultaneously in their dedicated directory without causing merge conflicts or architectural cross-talk.

---

## 🗺️ Team Ownership & Directory Map

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TEAM AREA 1: Models, Training Pipelines & Hybrid RAG                                   │
│ • Focus: Main Conductor, Sub-1B Specialists (M0–M12), Tokenizers, Qdrant/BM25          │
│ • Dedicated Paths:                                                                     │
│   ├── training/src/model/               (Model architectures & configs)               │
│   ├── training/scripts/                 (Dataset generation & training scripts)        │
│   ├── training/data/specialists/        (Curated specialist dataset files)             │
│   └── backend/src/xeren/rag/            (CAG cache, Qdrant store, BM25, RRF)           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TEAM AREA 2: Execution Engine, Sandboxing & Tool Infrastructure                        │
│ • Focus: ToolCaller dispatch, subprocess sandbox, Git branch isolation, MCP client     │
│ • Dedicated Paths:                                                                     │
│   ├── backend/automation_framework/mos/ (MOS Orchestrator, ToolCaller, Runners)        │
│   ├── backend/src/xeren/core/           (Runtime, governor, event bus)                 │
│   └── backend/src/xeren/mcp/            (Model Context Protocol client adapter)        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TEAM AREA 3: Frontend, Visual Identity & Milestone Panel                               │
│ • Focus: Glassmorphism living cloud avatar, progress cards, real-time WebSocket         │
│ • Dedicated Paths:                                                                     │
│   ├── frontend/src/components/          (UI cards, execution status, avatar)           │
│   ├── frontend/src/styles/              (Color palette tokens, glassmorphism CSS)      │
│   └── backend/src/xeren/server/         (FastAPI WebSocket endpoints & API routers)    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TEAM AREA 4: Memory Databases, ExperienceStore & Data Ingestion                        │
│ • Focus: SQLite/Postgres stores, anti-poison quarantine, causal tuple distillation     │
│ • Dedicated Paths:                                                                     │
│   ├── backend/src/xeren/plugins/experience/ (BaseStore, SQLiteStore, Quarantine)      │
│   ├── data/                             (Local DBs, qdrant index, unreviewed JSONL)    │
│   └── backend/src/xeren/db/             (Database connection pooling & migrations)     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TEAM AREA 5: Security, Verification & Academic Evaluation                              │
│ • Focus: 8-Layer security, UserVault, M9 Critic, M10 Verifier, Xeren-Bench             │
│ • Dedicated Paths:                                                                     │
│   ├── backend/src/xeren/security/       (Permissions, token enclaves, step-up auth)   │
│   ├── backend/src/xeren/eval/           (12-Faculty scorecard & metrics)               │
│   └── tests/benchmarks/                 (Xeren-Bench student engineering challenges)   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📜 Team Development Rules (Section 18 & 19 of Handoff Protocol)

1. **Strict Area Independence**: Work inside your designated area. Do not modify another team's core files without prior review.
2. **Deterministic Protocol Contracts**: All inter-model communication MUST adhere to [protocol.py](file:///c:/Users/leela/Dropbox/Xeren/backend/automation_framework/mos/protocol.py).
3. **No Scratch/Garbage Data**: All training data manufactured in `training/data/` must pass AST parsing (`ast.parse`) and schema validation.
4. **Zero Silent Merges**: Run unit tests (`pytest tests/<your_area>/`) before opening a pull request.
5. **Living Matrix Updates**: Once your component is completed and tests pass 100%, update [xeren_52_ideas_blueprint.md](file:///c:/Users/leela/Dropbox/Xeren/xeren_52_ideas_blueprint.md) to promote it from **🟡 In Development** to **🟢 Implemented**.

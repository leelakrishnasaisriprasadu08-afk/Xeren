# Xeren — Autonomous AI Workstation & Mixture of Specialists (MoS)

Xeren is an extensible, autonomous agentic AI workstation powered by native language models, a specialized Mixture of Specialists (MoS) routing architecture, and full-stack automation.

---

## 📁 Repository Organization

The repository is organized into three distinct layers:

```
Xeren/
├── frontend/                 # 🌐 1. FRONTEND: React 18, Vite, TypeScript, Tailwind
├── backend/                  # ⚙️ 2. BACKEND: FastAPI Server, Agent Runtime, MoS Engine
│   ├── src/xeren/            # Core backend app, server, DB, RAG, auth, models
│   └── automation_framework/ # Mixture of Specialists (MoS) & Automation
│
├── training/                 # 🔬 3. OTHERS: Native Transformer, Datasets, Checkpoints
├── scripts/                  # 🔬 3. OTHERS: Launch scripts, CLI chats, Verification
├── tests/                    # 🔬 3. OTHERS: Unit, integration, and browser tests
├── docs/                     # 🔬 3. OTHERS: Architecture guides and system specs
└── data/                     # 🔬 3. OTHERS: Vector databases, local storage, state
```

For complete file-by-file details, see the [Project Structure Guide](docs/PROJECT_STRUCTURE.md).

---

## 🚀 Quickstart

### 1. Launch Backend
```bash
npm run backend
# Starts FastAPI server at http://127.0.0.1:8000
```

### 2. Launch Frontend
```bash
npm run dev
# Starts Vite dev server at http://localhost:5173
```

### 3. Interactive CLI Chat
```bash
npm run chat
```

### 4. MoS & Model Training
```bash
# Smoke test the Mixture of Specialists pipeline
python automation_framework/mos/test_mos_pipeline.py

# Run Main Orchestrator dry run
python training/scripts/train_main_orchestrator.py --dry-run

# Run ToolCaller dry run
python training/scripts/train_tool_caller.py --dry-run
```


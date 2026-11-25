# Xeren Architecture

## Core Goal

Xeren is a real-time personal AI system that can understand natural language,
reason about goals, use authorized tools, maintain memory, and execute tasks
through a secure permission system.

## Core Loop

User Input
→ Conversation
→ Reasoning
→ Planning
→ Permission Check
→ Tool Execution
→ Result
→ Verification
→ Memory
→ Response

## Major Subsystems

- Core Runtime
- Conversation
- Reasoning
- Planning
- Memory
- RAG
- Tools
- Security & Permissions
- Tasks
- Models & Training Foundation
- Training Data & Curation Pipeline
- Evaluation & Verification

## Learning Paths

1. **Model Learning (Weights)**:
   - Offline fine-tuning of specialized open-weight models on verified agent trajectories (SFT Chat, Structured Agent tokens, DPO preference pairs).
   - Training pipeline: `Raw Experience → Curation & Anti-Contradiction → Tokenizer → Base Model → Trainer → Evaluation → Specialized Weights`.

2. **Runtime Experience Learning (Context)**:
   - Online memory capturing execution history, verification scores, self-corrections, and environment adaptations.
   - Immediate feedback loop without immediate weight updates.

## Design Principles

1. Security before powerful actions.
2. Every external action must be authorized.
3. Components should remain modular.
4. Model providers must be replaceable; training pipelines support custom specialized open-weight models.
5. Every important action should be observable.
6. Failed actions must be recoverable.
7. AI-generated code must be tested before integration.
8. Human approval is required for dangerous or irreversible operations.
9. Training data must enforce empirical verification, quality gates, and anti-contradiction constraints.

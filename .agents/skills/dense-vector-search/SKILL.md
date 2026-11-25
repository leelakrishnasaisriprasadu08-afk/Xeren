---
name: dense-vector-search
description: >-
  Use this skill when semantic meaning, architectural concepts, natural language
  intent, or broad behavioral queries need to be retrieved from the Qdrant vector store.
---

# Dense Vector Search Skill

Provides semantic dense vector search over the `xeren_codebase` collection in Qdrant using the `all-MiniLM-L6-v2` embedding model.

## When to Use
- The user describes functionality conceptually without mentioning exact symbol names.
- Finding similar design patterns, workflows, or documentation blocks.
- Fuzzy or exploratory codebase queries where keywords may vary.

## How to Call
Invoke the tool `query_embeddings` on the `Dense_Vector_Search` MCP server:

```python
query_embeddings(
    query="How does the authentication policy gate verify retrieved evidence?",
    limit=5
)
```

## Policy Gate Verification
Before using retrieved chunks in downstream generation, validate each piece of evidence with the Policy Gate:
```python
from src.rag.verifier import parse_evidence_verification

verdict = parse_evidence_verification({
    "IS_RELEVANT": True,
    "IS_SUPPORTED": True,
    "HAS_PERMISSION": True,
    "VERDICT": "PASS",
    "correction_hint": ""
})
```

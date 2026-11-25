---
name: bm25-lexical-search
description: >-
  Use this skill when exact keyword matches, symbol names, function signatures,
  variable identifiers, or specific code snippets need to be retrieved from the
  SQLite code chunk index.
---

# BM25 Lexical Search Skill

Provides exact-match keyword and lexical token retrieval across indexed code chunks using the BM25Okapi ranking algorithm.

## When to Use
- The user asks to find a specific function, class, variable, or symbol name.
- The query contains exact error strings, configuration keys, or verbatim code lines.
- Semantic vector retrieval is insufficient due to rare or syntactically precise tokens.

## How to Call
Invoke the tool `execute_search` on the `BM25_Lexical_Search` MCP server:

```python
execute_search(
    query="def authenticate_user",
    top_k=5
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

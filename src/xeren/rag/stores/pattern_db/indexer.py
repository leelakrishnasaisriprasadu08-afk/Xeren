"""In-memory multi-pattern indexing engine for the Xeren Sovereign Pattern DB.

Features:
- Vectorized CPU dense matrix cosine similarity using NumPy.
- Sparse inverted token index with frequency/relevance weighting.
- AST symbol and syntactic construct index (functions, classes, calls).
- Hierarchical document and section tree graph index.
- Faceted multi-attribute index for zero-latency metadata filtering.
"""

from collections import defaultdict
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from xeren.rag.stores.pattern_db.schema import PatternRecord, PatternType


class PatternIndexer:
    """Manages high-speed in-memory multi-pattern indices."""

    def __init__(self) -> None:
        # Records registry: pattern_id -> PatternRecord
        self.records: Dict[str, PatternRecord] = {}

        # Dense Vector Index
        self._dense_ids: List[str] = []
        self._dense_matrix: Optional[np.ndarray] = None  # Shape (N, D), normalized

        # Sparse Lexical Token Inverted Index: token -> set(pattern_id)
        self._lexical_index: Dict[str, Set[str]] = defaultdict(set)

        # AST / Code Pattern Index:
        # symbol_name (lowercased) -> set(pattern_id)
        self._ast_symbol_index: Dict[str, Set[str]] = defaultdict(set)
        # ast_node_type (e.g. "FunctionDef", "ClassDef") -> set(pattern_id)
        self._ast_type_index: Dict[str, Set[str]] = defaultdict(set)

        # Hierarchical Index:
        # parent_chunk_id -> list of child pattern_ids
        self._parent_to_children: Dict[str, List[str]] = defaultdict(list)
        # child_chunk_id -> parent_chunk_id
        self._child_to_parent: Dict[str, str] = {}
        # chunk_id -> list of pattern_ids associated with this chunk
        self._chunk_to_patterns: Dict[str, List[str]] = defaultdict(list)

        # Faceted Index: facet_key -> facet_value -> set(pattern_id)
        self._faceted_index: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

        # Rebuild dirty flag for vector matrix
        self._dense_matrix_dirty: bool = True

    def index_record(self, record: PatternRecord) -> None:
        """Add a pattern record into all relevant pattern indices."""
        pid = record.pattern_id
        self.records[pid] = record
        self._chunk_to_patterns[record.chunk_id].append(pid)

        # 1. Dense Vector Index
        if record.vector is not None and len(record.vector) > 0:
            if pid not in self._dense_ids:
                self._dense_ids.append(pid)
            self._dense_matrix_dirty = True

        # 2. Sparse Lexical Index
        tokens = self._tokenize(record.signature)
        if record.sparse_weights:
            tokens.update(record.sparse_weights.keys())
        for token in tokens:
            self._lexical_index[token].add(pid)

        # 3. AST / Code Pattern Index
        if record.pattern_type == PatternType.CODE_AST:
            sym = record.signature.strip().lower()
            if sym:
                self._ast_symbol_index[sym].add(pid)
            node_type = record.features.get("node_type")
            if node_type:
                self._ast_type_index[str(node_type)].add(pid)
            # Index arguments or calls if present
            calls = record.features.get("calls", [])
            for call_name in calls:
                self._ast_symbol_index[str(call_name).strip().lower()].add(pid)

        # 4. Hierarchical Index
        if record.pattern_type == PatternType.HIERARCHICAL:
            parent_id = record.features.get("parent_chunk_id")
            if parent_id:
                self._parent_to_children[str(parent_id)].append(pid)
                self._child_to_parent[record.chunk_id] = str(parent_id)


        # 5. Faceted Index
        for k, v in record.features.items():
            if isinstance(v, (str, int, float, bool)):
                self._faceted_index[str(k)][str(v)].add(pid)
        for k, v in record.payload.items():
            if isinstance(v, (str, int, float, bool)):
                self._faceted_index[str(k)][str(v)].add(pid)

    def remove_record(self, pattern_id: str) -> bool:
        """Remove a pattern record from all indices."""
        if pattern_id not in self.records:
            return False

        record = self.records.pop(pattern_id)

        # Remove from dense list
        if pattern_id in self._dense_ids:
            self._dense_ids.remove(pattern_id)
            self._dense_matrix_dirty = True

        # Remove from lexical
        tokens = self._tokenize(record.signature)
        if record.sparse_weights:
            tokens.update(record.sparse_weights.keys())
        for token in tokens:
            self._lexical_index[token].discard(pattern_id)

        # Remove from AST
        if record.pattern_type == PatternType.CODE_AST:
            sym = record.signature.strip().lower()
            self._ast_symbol_index[sym].discard(pattern_id)
            node_type = record.features.get("node_type")
            if node_type:
                self._ast_type_index[str(node_type)].discard(pattern_id)

        # Remove from chunk mapping
        chunk_patterns = self._chunk_to_patterns.get(record.chunk_id, [])
        if pattern_id in chunk_patterns:
            chunk_patterns.remove(pattern_id)

        # Remove from hierarchy
        parent_id = record.features.get("parent_chunk_id")
        if parent_id and parent_id in self._parent_to_children:
            if pattern_id in self._parent_to_children[parent_id]:
                self._parent_to_children[parent_id].remove(pattern_id)

        # Remove from faceted
        for k, v in record.features.items():
            if isinstance(v, (str, int, float, bool)):
                self._faceted_index[str(k)][str(v)].discard(pattern_id)

        return True

    def clear(self) -> None:
        """Clear all in-memory indices."""
        self.records.clear()
        self._dense_ids.clear()
        self._dense_matrix = None
        self._dense_matrix_dirty = True
        self._lexical_index.clear()
        self._ast_symbol_index.clear()
        self._ast_type_index.clear()
        self._parent_to_children.clear()
        self._child_to_parent.clear()
        self._chunk_to_patterns.clear()
        self._faceted_index.clear()

    # -------------------------------------------------------------------------
    # Multi-Pattern Search Routines
    # -------------------------------------------------------------------------

    def search_dense(
        self,
        query_vector: List[float],
        top_k: int = 5,
        candidate_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[PatternRecord, float]]:
        """Perform vectorized cosine similarity search over dense patterns."""
        if not self._dense_ids or not query_vector:
            return []

        self._ensure_dense_matrix()
        if self._dense_matrix is None or len(self._dense_ids) == 0:
            return []

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0.0:
            return []
        q_vec = q_vec / q_norm

        # Vectorized dot product (cosine similarity since both normalized)
        # dense_matrix shape: (N, D), q_vec shape: (D,)
        # similarities shape: (N,)
        similarities = np.dot(self._dense_matrix, q_vec)

        results: List[Tuple[PatternRecord, float]] = []
        for idx, score in enumerate(similarities):
            pid = self._dense_ids[idx]
            if candidate_ids is not None and pid not in candidate_ids:
                continue
            record = self.records.get(pid)
            if record:
                results.append((record, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_lexical(
        self,
        query_text: str,
        top_k: int = 5,
        candidate_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[PatternRecord, float]]:
        """Sparse lexical scoring based on token overlap and term weighting."""
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)
        for token in query_tokens:
            matched_pids = self._lexical_index.get(token, set())
            for pid in matched_pids:
                if candidate_ids is not None and pid not in candidate_ids:
                    continue
                record = self.records[pid]
                weight = 1.0
                if record.sparse_weights and token in record.sparse_weights:
                    weight = record.sparse_weights[token]
                scores[pid] += weight

        if not scores:
            return []

        ranked = [
            (self.records[pid], score)
            for pid, score in scores.items()
            if pid in self.records
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def search_ast(
        self,
        symbol_name: Optional[str] = None,
        node_type: Optional[str] = None,
        candidate_ids: Optional[Set[str]] = None,
    ) -> List[PatternRecord]:
        """Search code AST patterns by symbol name, method/call signature, or node type."""
        pids: Optional[Set[str]] = None

        if symbol_name:
            sym_clean = symbol_name.strip().lower()
            sym_matches = self._ast_symbol_index.get(sym_clean, set())
            # Also partial substring match for symbol if exact match is empty
            if not sym_matches:
                sym_matches = {
                    pid
                    for s, matches in self._ast_symbol_index.items()
                    if sym_clean in s
                    for pid in matches
                }
            pids = set(sym_matches)

        if node_type:
            type_matches = self._ast_type_index.get(node_type, set())
            if pids is None:
                pids = set(type_matches)
            else:
                pids = pids.intersection(type_matches)

        if pids is None:
            pids = {
                pid
                for pid, rec in self.records.items()
                if rec.pattern_type == PatternType.CODE_AST
            }

        if candidate_ids is not None:
            pids = pids.intersection(candidate_ids)

        return [self.records[pid] for pid in pids if pid in self.records]

    def filter_facets(self, filters: Dict[str, Any]) -> Set[str]:
        """Intersect pattern IDs matching all exact facet filters."""
        if not filters:
            return set(self.records.keys())

        matched_sets: List[Set[str]] = []
        for k, v in filters.items():
            val_str = str(v)
            if k in self._faceted_index and val_str in self._faceted_index[k]:
                matched_sets.append(self._faceted_index[k][val_str])
            else:
                return set()  # No record has this facet value

        if not matched_sets:
            return set()

        result = set(matched_sets[0])
        for s in matched_sets[1:]:
            result = result.intersection(s)
        return result

    def get_children(self, parent_chunk_id: str) -> List[PatternRecord]:
        """Retrieve all child pattern records belonging to a parent chunk."""
        child_pids = self._parent_to_children.get(parent_chunk_id, [])
        return [self.records[pid] for pid in child_pids if pid in self.records]

    def get_parent_id(self, child_chunk_id: str) -> Optional[str]:
        """Get the parent chunk ID for a given child chunk."""
        return self._child_to_parent.get(child_chunk_id)

    def get_chunk_patterns(self, chunk_id: str) -> List[PatternRecord]:
        """Get all pattern records associated with a specific DocumentChunk."""
        pids = self._chunk_to_patterns.get(chunk_id, [])
        return [self.records[pid] for pid in pids if pid in self.records]

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _ensure_dense_matrix(self) -> None:
        """Rebuild or update the normalized NumPy matrix of dense vectors."""
        if not self._dense_matrix_dirty:
            return

        if not self._dense_ids:
            self._dense_matrix = None
            self._dense_matrix_dirty = False
            return

        vectors: List[List[float]] = []
        valid_ids: List[str] = []

        for pid in self._dense_ids:
            rec = self.records.get(pid)
            if rec and rec.vector is not None and len(rec.vector) > 0:
                vectors.append(rec.vector)
                valid_ids.append(pid)

        if not vectors:
            self._dense_ids = []
            self._dense_matrix = None
            self._dense_matrix_dirty = False
            return

        self._dense_ids = valid_ids
        matrix = np.array(vectors, dtype=np.float32)

        # L2-normalize each row for fast cosine calculation
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0.0] = 1.0
        self._dense_matrix = matrix / norms
        self._dense_matrix_dirty = False

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Extract alphanumeric tokens, code identifiers, and snake/camel case tokens."""
        if not text:
            return set()
        # Find alphanumeric runs and code words
        words = re.findall(r"[A-Za-z0-9_]+", text.lower())
        tokens: Set[str] = set()
        for w in words:
            if len(w) > 1:
                tokens.add(w)
                # Split snake_case
                parts = w.split("_")
                if len(parts) > 1:
                    tokens.update(p for p in parts if len(p) > 1)
        return tokens

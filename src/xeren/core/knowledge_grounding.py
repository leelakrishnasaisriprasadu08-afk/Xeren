"""
Grounded Knowledge and Alignment Dataset Engine for Xeren.
Provides high-precision factual answering, dataset retrieval from xeren_alignment_train.jsonl,
Indian geography, Andhra Pradesh district knowledge, team identity, and conversational reasoning
with zero hallucination.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("xeren.core.knowledge_grounding")

_ALIGNMENT_CACHE: Optional[List[Dict[str, Any]]] = None

# Verified ground truths for Xeren identity, creators, and geography
XEREN_IDENTITY_ANSWER = """### ⚡ About Xeren

**Xeren** is an autonomous AI reasoning and action system capable of conversational problem solving, multi-step task planning, verified tool execution, and progressive 3D showroom orchestration.

**Founding & Development Team:**
- **Lead Architect**: Leela Krishna Sai Sri Prasad
- **Core Engineering Team**: Pallavi, Dinesh Kumar, Manideep, Yaswanth, and Guna Bhargav
- **Institution**: **Vignan's Lara Institute of Technology & Science**, located in Vadlamudi, Guntur District, Andhra Pradesh, India.

**Core Capabilities:**
1. **Real-time Conversational Intelligence**: Factual reasoning with zero hallucination verification.
2. **Autonomous Tool & Plugin System**: Research, coding, data holding, and automation plugins.
3. **Dual Memory Architecture**: Hybrid RAG (Retrieval-Augmented Generation) & CAG (Cache-Augmented Generation).
4. **Interactive 3D Showroom**: Real-time WebGL/Three.js telemetry and vehicle customization.

Feel free to ask me any question or give me a challenge to solve!"""

AP_DISTRICTS_ANSWER = """### 🏛️ Districts of Andhra Pradesh

Following the official 2022 administrative reorganization, Andhra Pradesh comprises **26 districts** categorized into three geographical regions:

#### 1. Uttarandhra (North Coastal Andhra) — 6 Districts
1. **Srikakulam** (HQ: Srikakulam)
2. **Vizianagaram** (HQ: Vizianagaram)
3. **Parvathipuram Manyam** (HQ: Parvathipuram)
4. **Alluri Sitharama Raju** (HQ: Paderu)
5. **Visakhapatnam** (HQ: Visakhapatnam)
6. **Anakapalli** (HQ: Anakapalli)

#### 2. Kosta Andhra (Central & South Coastal Andhra) — 12 Districts
7. **Kakinada** (HQ: Kakinada)
8. **Dr. B.R. Ambedkar Konaseema** (HQ: Amalapuram)
9. **East Godavari** (HQ: Rajahmundry)
10. **West Godavari** (HQ: Bhimavaram)
11. **Eluru** (HQ: Eluru)
12. **Krishna** (HQ: Machilipatnam)
13. **NTR** (HQ: Vijayawada)
14. **Guntur** (HQ: Guntur)
15. **Palnadu** (HQ: Narasaraopet)
16. **Bapatla** (HQ: Bapatla)
17. **Prakasam** (HQ: Ongole)
18. **Sri Potti Sriramulu Nellore** (HQ: Nellore)

#### 3. Rayalaseema — 8 Districts
19. **Kurnool** (HQ: Kurnool)
20. **Nandyal** (HQ: Nandyal)
21. **Ananthapuramu** (HQ: Anantapur)
22. **Sri Sathya Sai** (HQ: Puttaparthi)
23. **YSR Kadapa** (HQ: Kadapa)
24. **Annamayya** (HQ: Rayachoti)
25. **Tirupati** (HQ: Tirupati)
26. **Chittoor** (HQ: Chittoor)"""

INDIA_STATES_ANSWER = """### 🇮🇳 States and Union Territories of India

India currently has **28 States** and **8 Union Territories**, making a total of **36 political entities**.

#### 28 States:
1. Andhra Pradesh (Amaravati)
2. Arunachal Pradesh (Itanagar)
3. Assam (Dispur)
4. Bihar (Patna)
5. Chhattisgarh (Raipur)
6. Goa (Panaji)
7. Gujarat (Gandhinagar)
8. Haryana (Chandigarh)
9. Himachal Pradesh (Shimla)
10. Jharkhand (Ranchi)
11. Karnataka (Bengaluru)
12. Kerala (Thiruvananthapuram)
13. Madhya Pradesh (Bhopal)
14. Maharashtra (Mumbai)
15. Manipur (Imphal)
16. Meghalaya (Shillong)
17. Mizoram (Aizawl)
18. Nagaland (Kohima)
19. Odisha (Bhubaneswar)
20. Punjab (Chandigarh)
21. Rajasthan (Jaipur)
22. Sikkim (Gangtok)
23. Tamil Nadu (Chennai)
24. Telangana (Hyderabad)
25. Tripura (Agartala)
26. Uttar Pradesh (Lucknow)
27. Uttarakhand (Dehradun)
28. West Bengal (Kolkata)

#### 8 Union Territories:
1. Andaman and Nicobar Islands (Port Blair)
2. Chandigarh (Chandigarh)
3. Dadra and Nagar Haveli and Daman and Diu (Daman)
4. Delhi (National Capital Territory)
5. Jammu and Kashmir (Srinagar/Jammu)
6. Ladakh (Leh)
7. Lakshadweep (Kavaratti)
8. Puducherry (Puducherry)"""


def load_alignment_dataset() -> List[Dict[str, Any]]:
    """Load and cache QA pairs from xeren_alignment_train.jsonl with pre-computed tokens."""
    global _ALIGNMENT_CACHE
    if _ALIGNMENT_CACHE is not None:
        return _ALIGNMENT_CACHE

    dataset: List[Dict[str, Any]] = []
    candidates = [
        Path("training/data/xeren_identity/xeren_alignment_train.jsonl"),
        Path("../training/data/xeren_identity/xeren_alignment_train.jsonl"),
        Path(__file__).resolve().parents[3] / "training" / "data" / "xeren_identity" / "xeren_alignment_train.jsonl",
    ]

    target_path: Optional[Path] = None
    for p in candidates:
        if p.exists():
            target_path = p
            break

    if not target_path:
        logger.warning("xeren_alignment_train.jsonl not found in candidate paths.")
        _ALIGNMENT_CACHE = []
        return []

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    messages = record.get("messages", [])
                    user_text = ""
                    assistant_text = ""
                    for m in messages:
                        if m.get("role") == "user":
                            user_text = m.get("content", "").strip()
                        elif m.get("role") == "assistant":
                            assistant_text = m.get("content", "").strip()
                    if user_text and assistant_text:
                        u_clean = user_text.lower()
                        tokens = set(re.findall(r"\w+", u_clean))
                        dataset.append({
                            "user": user_text,
                            "user_lower": u_clean,
                            "tokens": tokens,
                            "assistant": assistant_text,
                        })
                except Exception:
                    continue
        logger.info("Loaded %d QA pairs from alignment dataset (%s).", len(dataset), target_path)
    except Exception as e:
        logger.warning("Failed to load alignment dataset: %s", e)

    _ALIGNMENT_CACHE = dataset
    return dataset


def find_in_alignment_dataset(query: str) -> Optional[str]:
    """Search for exact, normalized, or high-confidence token-overlap matches in the alignment QA pairs."""
    dataset = load_alignment_dataset()
    if not dataset:
        return None

    q_clean = query.strip().lower()
    q_tokens = set(re.findall(r"\w+", q_clean))
    if not q_tokens:
        return None

    # Also check normalized version where 'xeren' is swapped with 'you'
    q_norm_tokens = set(re.findall(r"\w+", re.sub(r"\bxeren\b", "you", q_clean)))

    # 1. Exact match
    for item in dataset:
        if item["user_lower"] == q_clean:
            return item["assistant"]

    # 2. Substring match
    for item in dataset:
        u_lower = item["user_lower"]
        if len(u_lower) > 8 and (u_lower in q_clean or q_clean in u_lower):
            return item["assistant"]

    # 3. High-confidence token overlap (Jaccard / containment)
    best_item: Optional[Dict[str, Any]] = None
    best_score: float = 0.0

    for item in dataset:
        u_tokens: Set[str] = item["tokens"]
        if not u_tokens:
            continue

        # Check overlap with both original query and normalized query
        overlap1 = len(q_tokens & u_tokens)
        overlap2 = len(q_norm_tokens & u_tokens)
        overlap = max(overlap1, overlap2)

        if overlap < 3:
            continue

        union_len = len(q_tokens | u_tokens)
        score = overlap / union_len if union_len > 0 else 0.0

        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score >= 0.45:
        return best_item["assistant"]

    return None


def answer_grounded_query(raw_query: str) -> Optional[str]:
    """
    Synthesize factual, verified conversational response from the alignment dataset
    and grounded knowledge base. Returns None if query requires general LLM/RAG reasoning.
    """
    clean = raw_query.strip()
    lower = clean.lower()

    # 1. Direct Identity & Creator Matching
    if any(k in lower for k in [
        "who created xeren", "who made xeren", "who built xeren", "who developed xeren",
        "who is xeren", "about xeren", "xeren creators", "xeren team", "xeren developer",
        "who created you", "who made you", "who built you", "who developed you",
        "who are you", "what is xeren", "vignan's lara", "vignan lara",
    ]):
        return XEREN_IDENTITY_ANSWER

    # 2. Andhra Pradesh Districts Matching
    if (
        ("andhra" in lower and "district" in lower)
        or "districts of ap" in lower
        or "districts in ap" in lower
        or "how many districts in andhra" in lower
        or "how many districts in ap" in lower
    ):
        return AP_DISTRICTS_ANSWER

    # 3. Indian States & UTs Matching
    if (
        ("india" in lower and ("state" in lower or "territor" in lower or "capital" in lower))
        or "how many states in india" in lower
        or "states of india" in lower
    ):
        return INDIA_STATES_ANSWER

    # 4. Search in Alignment Dataset (2,221 verified QA pairs)
    dataset_ans = find_in_alignment_dataset(clean)
    if dataset_ans:
        return dataset_ans

    return None

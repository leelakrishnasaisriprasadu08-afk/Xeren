"""Continuous Training Buffer — Hybrid Local JSONL + Supabase PostgreSQL.

Architecture:
  1. Write Path (Instant, ~microseconds):
     User request arrives → XerenTrainer records episode → Local JSONL buffer
     
  2. Flush Path (Background, every N episodes or 5 minutes):
     Local buffer → Bulk insert into Supabase experiencerecord table
     
  3. Training Pull Path (Continuous Trainer):
     Supabase → Pull new unflushed episodes → Format as ChatML → Fine-tune step

This ensures:
  - Zero latency for user-facing request handling (local write)
  - Zero data loss across restarts (Supabase persistence)
  - Support for concurrent multi-user episode recording (Supabase atomic inserts)
  - Continuous LLM improvement from real usage patterns
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.training.continuous_buffer")


# =============================================================================
# Schema for a Training Episode
# =============================================================================

def make_episode(
    user_query: str,
    assistant_response: str,
    plugin: str = "conversation",
    thought: Optional[str] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    quality_score: float = 1.0,
    session_id: Optional[str] = None,
    source: str = "user_interaction",
) -> Dict[str, Any]:
    """Create a structured training episode dict."""
    return {
        "episode_id": str(uuid.uuid4()),
        "session_id": session_id or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": source,  # user_interaction | web_result | synthetic
        "plugin": plugin,
        "user": user_query,
        "thought": thought or f"Processing user request via {plugin} plugin.",
        "assistant": assistant_response,
        "tool_calls": tool_calls or [],
        "quality_score": quality_score,
        "flushed_to_db": False,
    }


# =============================================================================
# Local JSONL Buffer (instant writes)
# =============================================================================

class LocalEpisodeBuffer:
    """Thread-safe local JSONL buffer for continuous training episodes.
    
    Writes are instant (append-to-file, ~microseconds).
    Designed to buffer episodes before batch-uploading to Supabase.
    """

    def __init__(self, buffer_path: str = "data/continuous_training/new_sessions.jsonl"):
        self.buffer_path = Path(buffer_path)
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_count = 0

    def record(self, episode: Dict[str, Any]) -> None:
        """Append a training episode to the local JSONL buffer. Instant write."""
        try:
            with open(self.buffer_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode, ensure_ascii=False) + "\n")
            self._write_count += 1
            logger.debug(f"Buffered episode #{self._write_count}: {episode['episode_id'][:8]}")
        except Exception as e:
            logger.error(f"Failed to write episode to buffer: {e}")

    def record_interaction(
        self,
        user_query: str,
        assistant_response: str,
        plugin: str = "conversation",
        thought: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        quality_score: float = 1.0,
        session_id: Optional[str] = None,
    ) -> str:
        """High-level method: record a user interaction episode. Returns episode_id."""
        episode = make_episode(
            user_query=user_query,
            assistant_response=assistant_response,
            plugin=plugin,
            thought=thought,
            tool_calls=tool_calls,
            quality_score=quality_score,
            session_id=session_id,
            source="user_interaction",
        )
        self.record(episode)
        return episode["episode_id"]

    def record_web_result(
        self,
        query: str,
        web_content: str,
        synthesized_answer: str,
        quality_score: float = 0.85,
    ) -> str:
        """Record a web search result episode for continuous learning."""
        episode = make_episode(
            user_query=query,
            assistant_response=synthesized_answer,
            plugin="research",
            thought=f"Web search result synthesized for: {query}",
            tool_calls=[{"tool": "web_search", "args": {"query": query}, "result": web_content[:500]}],
            quality_score=quality_score,
            source="web_result",
        )
        self.record(episode)
        return episode["episode_id"]

    def load_unflushed(self, max_episodes: int = 500) -> List[Dict[str, Any]]:
        """Load episodes that have not yet been flushed to Supabase."""
        episodes = []
        if not self.buffer_path.exists():
            return episodes
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ep = json.loads(line)
                        if not ep.get("flushed_to_db", False):
                            episodes.append(ep)
                            if len(episodes) >= max_episodes:
                                break
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Failed to load buffer: {e}")
        return episodes

    def mark_flushed(self, episode_ids: List[str]) -> None:
        """Mark episodes as flushed in the local buffer (rewrite file)."""
        if not self.buffer_path.exists():
            return
        flushed_set = set(episode_ids)
        updated_lines = []
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ep = json.loads(line)
                        if ep.get("episode_id") in flushed_set:
                            ep["flushed_to_db"] = True
                        updated_lines.append(json.dumps(ep, ensure_ascii=False))
                    except Exception:
                        updated_lines.append(line)
            with open(self.buffer_path, "w", encoding="utf-8") as f:
                f.write("\n".join(updated_lines) + "\n")
        except Exception as e:
            logger.error(f"Failed to mark episodes as flushed: {e}")

    @property
    def total_buffered(self) -> int:
        """Count total episodes in the buffer file."""
        if not self.buffer_path.exists():
            return 0
        count = 0
        with open(self.buffer_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count


# =============================================================================
# Supabase Flusher (background batch upload)
# =============================================================================

class SupabaseFlusher:
    """Batch-uploads buffered episodes to Supabase experiencerecord table.
    
    The experiencerecord table schema:
      id           TEXT PRIMARY KEY (episode_id)
      session_id   TEXT
      timestamp    TIMESTAMP
      source       TEXT
      plugin       TEXT
      user_query   TEXT
      thought      TEXT
      assistant    TEXT
      tool_calls   JSONB
      quality_score FLOAT
      trained_on   BOOLEAN DEFAULT FALSE
    """

    def __init__(self, postgres_uri: Optional[str] = None):
        self.uri = postgres_uri or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URI", "")
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from sqlmodel import create_engine
                self._engine = create_engine(self.uri, pool_pre_ping=True, pool_size=2, max_overflow=5)
            except Exception as e:
                logger.error(f"Supabase engine creation failed: {e}")
        return self._engine

    def ensure_table_exists(self) -> bool:
        """Create the continuous_training_episodes table if it doesn't exist."""
        engine = self._get_engine()
        if not engine:
            return False
        try:
            from sqlmodel import text
            create_sql = """
            CREATE TABLE IF NOT EXISTS continuous_training_episodes (
                episode_id    VARCHAR(64) PRIMARY KEY,
                session_id    VARCHAR(64),
                timestamp     TIMESTAMP DEFAULT NOW(),
                source        VARCHAR(32) DEFAULT 'user_interaction',
                plugin        VARCHAR(32) DEFAULT 'conversation',
                user_query    TEXT,
                thought       TEXT,
                assistant     TEXT,
                tool_calls    TEXT,
                quality_score FLOAT DEFAULT 1.0,
                trained_on    BOOLEAN DEFAULT FALSE
            );
            """
            with engine.connect() as conn:
                conn.execute(text(create_sql))
                conn.commit()
            logger.info("Table continuous_training_episodes is ready.")
            return True
        except Exception as e:
            logger.error(f"Table creation failed: {e}")
            return False

    def flush(self, episodes: List[Dict[str, Any]]) -> List[str]:
        """Upload episodes to Supabase. Returns list of successfully uploaded episode IDs."""
        if not episodes:
            return []
        engine = self._get_engine()
        if not engine:
            logger.warning("Supabase unavailable — episodes remain in local buffer.")
            return []

        self.ensure_table_exists()
        flushed_ids = []
        try:
            from sqlmodel import text
            insert_sql = """
            INSERT INTO continuous_training_episodes
                (episode_id, session_id, timestamp, source, plugin, user_query, thought, assistant, tool_calls, quality_score)
            VALUES
                (:episode_id, :session_id, :timestamp, :source, :plugin, :user_query, :thought, :assistant, :tool_calls, :quality_score)
            ON CONFLICT (episode_id) DO NOTHING;
            """
            with engine.connect() as conn:
                for ep in episodes:
                    try:
                        conn.execute(text(insert_sql), {
                            "episode_id": ep["episode_id"],
                            "session_id": ep.get("session_id", ""),
                            "timestamp": ep.get("timestamp", datetime.utcnow().isoformat()),
                            "source": ep.get("source", "user_interaction"),
                            "plugin": ep.get("plugin", "conversation"),
                            "user_query": ep.get("user", ""),
                            "thought": ep.get("thought", ""),
                            "assistant": ep.get("assistant", ""),
                            "tool_calls": json.dumps(ep.get("tool_calls", [])),
                            "quality_score": ep.get("quality_score", 1.0),
                        })
                        flushed_ids.append(ep["episode_id"])
                    except Exception as e:
                        logger.warning(f"Failed to insert episode {ep.get('episode_id', '?')[:8]}: {e}")
                conn.commit()
        except Exception as e:
            logger.error(f"Supabase flush failed: {e}")

        logger.info(f"Flushed {len(flushed_ids)}/{len(episodes)} episodes to Supabase.")
        return flushed_ids

    def pull_for_training(
        self,
        max_episodes: int = 200,
        min_quality_score: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Pull untrained high-quality episodes from Supabase for the continuous trainer."""
        engine = self._get_engine()
        if not engine:
            return []
        try:
            from sqlmodel import text
            query = """
            SELECT episode_id, plugin, user_query, thought, assistant, tool_calls, quality_score
            FROM continuous_training_episodes
            WHERE trained_on = FALSE AND quality_score >= :min_quality
            ORDER BY timestamp ASC
            LIMIT :limit;
            """
            with engine.connect() as conn:
                rows = conn.execute(text(query), {
                    "min_quality": min_quality_score,
                    "limit": max_episodes,
                }).fetchall()

            episodes = []
            for row in rows:
                episodes.append({
                    "episode_id": row[0],
                    "plugin": row[1],
                    "user": row[2],
                    "thought": row[3],
                    "assistant": row[4],
                    "tool_calls": json.loads(row[5]) if row[5] else [],
                    "quality_score": float(row[6]),
                })
            logger.info(f"Pulled {len(episodes)} untrained episodes from Supabase for continuous training.")
            return episodes
        except Exception as e:
            logger.error(f"Failed to pull episodes from Supabase: {e}")
            return []

    def mark_trained(self, episode_ids: List[str]) -> None:
        """Mark episodes as trained_on=TRUE in Supabase."""
        if not episode_ids:
            return
        engine = self._get_engine()
        if not engine:
            return
        try:
            from sqlmodel import text
            placeholders = ", ".join(f":id_{i}" for i in range(len(episode_ids)))
            update_sql = f"UPDATE continuous_training_episodes SET trained_on = TRUE WHERE episode_id IN ({placeholders});"
            params = {f"id_{i}": eid for i, eid in enumerate(episode_ids)}
            with engine.connect() as conn:
                conn.execute(text(update_sql), params)
                conn.commit()
            logger.info(f"Marked {len(episode_ids)} episodes as trained.")
        except Exception as e:
            logger.error(f"Failed to mark episodes as trained: {e}")


# =============================================================================
# Hybrid Buffer Manager (orchestrates both)
# =============================================================================

class HybridContinuousBuffer:
    """Orchestrates the full hybrid continuous training buffer lifecycle.
    
    Usage:
        buffer = HybridContinuousBuffer()
        
        # On every user request (instant, non-blocking):
        buffer.record_interaction(user_query, assistant_response, plugin="coding")
        
        # In background every 5 minutes:
        buffer.flush_to_supabase()
        
        # In continuous trainer:
        episodes = buffer.pull_for_training()
    """

    def __init__(
        self,
        buffer_path: str = "data/continuous_training/new_sessions.jsonl",
        postgres_uri: Optional[str] = None,
        auto_flush_threshold: int = 100,
    ):
        self.local_buffer = LocalEpisodeBuffer(buffer_path=buffer_path)
        self.supabase_flusher = SupabaseFlusher(postgres_uri=postgres_uri)
        self.auto_flush_threshold = auto_flush_threshold
        self._episode_count_since_flush = 0

    def record_interaction(
        self,
        user_query: str,
        assistant_response: str,
        plugin: str = "conversation",
        thought: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        quality_score: float = 1.0,
        session_id: Optional[str] = None,
    ) -> str:
        """Record a user interaction. Instant local write. Auto-flushes at threshold."""
        episode_id = self.local_buffer.record_interaction(
            user_query=user_query,
            assistant_response=assistant_response,
            plugin=plugin,
            thought=thought,
            tool_calls=tool_calls,
            quality_score=quality_score,
            session_id=session_id,
        )
        self._episode_count_since_flush += 1

        # Auto-flush to Supabase when threshold is hit
        if self._episode_count_since_flush >= self.auto_flush_threshold:
            logger.info(f"Auto-flush threshold ({self.auto_flush_threshold}) reached. Flushing to Supabase...")
            self.flush_to_supabase()

        return episode_id

    def record_web_result(self, query: str, web_content: str, synthesized_answer: str) -> str:
        """Record a web search result for continuous learning."""
        return self.local_buffer.record_web_result(query, web_content, synthesized_answer)

    def flush_to_supabase(self) -> int:
        """Flush all unflushed local episodes to Supabase. Returns count flushed."""
        unflushed = self.local_buffer.load_unflushed(max_episodes=500)
        if not unflushed:
            logger.info("No unflushed episodes to upload.")
            return 0
        flushed_ids = self.supabase_flusher.flush(unflushed)
        if flushed_ids:
            self.local_buffer.mark_flushed(flushed_ids)
            self._episode_count_since_flush = 0
        return len(flushed_ids)

    def pull_for_training(
        self,
        max_episodes: int = 200,
        min_quality_score: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Pull episodes ready for continuous training from Supabase."""
        return self.supabase_flusher.pull_for_training(
            max_episodes=max_episodes,
            min_quality_score=min_quality_score,
        )

    def mark_trained(self, episode_ids: List[str]) -> None:
        """Mark episodes as trained in Supabase."""
        self.supabase_flusher.mark_trained(episode_ids)

    def status(self) -> Dict[str, Any]:
        """Return buffer health status."""
        return {
            "local_buffer_total": self.local_buffer.total_buffered,
            "episodes_since_last_flush": self._episode_count_since_flush,
            "auto_flush_threshold": self.auto_flush_threshold,
            "supabase_connected": self.supabase_flusher._get_engine() is not None,
        }


# Global singleton for use across Xeren system
hybrid_buffer = HybridContinuousBuffer(
    buffer_path="data/continuous_training/new_sessions.jsonl",
    postgres_uri=os.getenv("DATABASE_URL"),
    auto_flush_threshold=100,
)

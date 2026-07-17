"""
observability.py — per-call LLM tracing for BugBuddy.

Emits structured JSON lines to the Python logger (grab them with any log
aggregator) and optionally writes a local .jsonl trace file.

Also keeps a rolling in-memory window of the last 500 records so the
/api/stats endpoint can return live metrics without a database.

Set TRACE_FILE env var to a path to get persistent traces.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Generator

log = logging.getLogger(__name__)

_TRACE_FILE = Path(os.getenv("TRACE_FILE", "")) or None
_MAX_RECORDS_IN_MEMORY = 500

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model for one LLM call
# ---------------------------------------------------------------------------

@dataclass
class LLMCallRecord:
    """One LLM call — populated by _Span and emitted on context manager exit."""
    trace_id:          str
    issue_key:         str
    provider:          str
    model:             str
    cache_hit:         bool         = False
    prompt_tokens:     int          = 0
    completion_tokens: int          = 0
    latency_ms:        float        = 0.0
    chunk_index:       int          = 1
    total_chunks:      int          = 1
    guardrail_blocked: bool         = False
    pii_redactions:    int          = 0
    quality_score:     float | None = None
    rag_used:          bool         = False
    error:             str | None   = None
    timestamp:         str          = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def estimated_cost_usd(self) -> float:
        # Rough estimate using public 2025 pricing per 1M tokens
        # TODO: pull live pricing from a config file so this doesn't go stale
        PRICING: dict[str, tuple[float, float]] = {
            "gpt-4o":              (5.0,  15.0),
            "gpt-4o-mini":         (0.15,  0.6),
            "gpt-4-turbo":         (10.0, 30.0),
            "claude-3-5-sonnet-20241022": (3.0, 15.0),
            "claude-3-opus-20240229":     (15.0, 75.0),
            "gemini-2.0-flash":    (0.075, 0.3),
            "gemini-1.5-pro":      (1.25,  5.0),
        }
        in_price, out_price = PRICING.get(self.model, (5.0, 15.0))
        return (self.prompt_tokens * in_price + self.completion_tokens * out_price) / 1_000_000

    def to_log_dict(self) -> dict:
        d = asdict(self)
        d["total_tokens"]       = self.total_tokens
        d["estimated_cost_usd"] = round(self.estimated_cost_usd, 6)
        return d


# ---------------------------------------------------------------------------
# Span (context manager for a single call)
# ---------------------------------------------------------------------------

class _Span:
    """Mutable span for one LLM call — created inside tracer.trace()."""

    def __init__(self, trace_id: str, issue_key: str,
                 provider: str, model: str) -> None:
        self._record = LLMCallRecord(
            trace_id=trace_id, issue_key=issue_key,
            provider=provider, model=model,
        )
        self._start = time.perf_counter()

    def set_tokens(self, prompt: int = 0, completion: int = 0) -> None:
        self._record.prompt_tokens     = prompt
        self._record.completion_tokens = completion

    def set_cache_hit(self, hit: bool) -> None:
        self._record.cache_hit = hit

    def set_chunk(self, index: int, total: int) -> None:
        self._record.chunk_index  = index
        self._record.total_chunks = total

    def set_guardrail(self, blocked: bool, pii_count: int = 0) -> None:
        self._record.guardrail_blocked = blocked
        self._record.pii_redactions    = pii_count

    def set_quality(self, score: float) -> None:
        self._record.quality_score = score

    def set_rag_used(self, used: bool) -> None:
        self._record.rag_used = used

    def set_error(self, msg: str) -> None:
        self._record.error = msg

    def _finalise(self) -> LLMCallRecord:
        self._record.latency_ms = round(
            (time.perf_counter() - self._start) * 1000, 1
        )
        return self._record


# ---------------------------------------------------------------------------
# Tracer singleton
# ---------------------------------------------------------------------------

class Tracer:
    """Thread-safe LLM call tracer. One global instance (`tracer`) is exported at the bottom."""

    def __init__(self) -> None:
        self._records: deque[LLMCallRecord] = deque(maxlen=_MAX_RECORDS_IN_MEMORY)
        self._lock = Lock()
        self._seq  = 0
        self._trace_fh = None
        if _TRACE_FILE:
            try:
                self._trace_fh = open(_TRACE_FILE, "a", encoding="utf-8")  # noqa: WPS515
                logger.info("Observability: trace file \u2192 %s", _TRACE_FILE)
            except OSError as exc:
                logger.warning("Observability: cannot open trace file: %s", exc)

    def _next_id(self) -> str:
        with self._lock:
            self._seq += 1
            return f"bb-{self._seq:06d}"

    @contextmanager
    def trace(self, provider: str, model: str,
              issue_key: str = "UNKNOWN") -> Generator[_Span, None, None]:
        """Context manager — yields a Span; records result on exit."""
        span = _Span(self._next_id(), issue_key, provider, model)
        try:
            yield span
        except Exception as exc:
            span.set_error(str(exc))
            raise
        finally:
            record = span._finalise()
            self._emit(record)

    def _emit(self, record: LLMCallRecord) -> None:
        with self._lock:
            self._records.append(record)

        log_dict = record.to_log_dict()
        logger.info("LLM_CALL %s", json.dumps(log_dict))

        if self._trace_fh:
            try:
                self._trace_fh.write(json.dumps(log_dict) + "\n")
                self._trace_fh.flush()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Stats API  (for /api/stats endpoint)
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Aggregate statistics over all in-memory records."""
        with self._lock:
            records = list(self._records)

        if not records:
            return {"total_calls": 0}

        total      = len(records)
        cache_hits = sum(1 for r in records if r.cache_hit)
        errors     = sum(1 for r in records if r.error)
        blocked    = sum(1 for r in records if r.guardrail_blocked)
        latencies  = [r.latency_ms for r in records if not r.cache_hit]
        tokens     = sum(r.total_tokens for r in records)
        cost       = sum(r.estimated_cost_usd for r in records)

        by_provider: dict[str, int] = {}
        for r in records:
            by_provider[r.provider] = by_provider.get(r.provider, 0) + 1

        quality_scores = [r.quality_score for r in records if r.quality_score is not None]

        return {
            "total_calls":          total,
            "cache_hit_rate":       round(cache_hits / total, 3),
            "error_rate":           round(errors / total, 3),
            "guardrail_block_rate": round(blocked / total, 3),
            "avg_latency_ms":       round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "p95_latency_ms":       round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if latencies else 0,
            "total_tokens":         tokens,
            "estimated_cost_usd":   round(cost, 4),
            "calls_by_provider":    by_provider,
            "avg_quality_score":    round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
        }

    def recent(self, n: int = 20) -> list[dict]:
        """Return the N most recent call records as dicts."""
        with self._lock:
            records = list(self._records)[-n:]
        return [r.to_log_dict() for r in reversed(records)]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
tracer = Tracer()

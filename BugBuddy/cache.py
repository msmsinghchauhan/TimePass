"""
cache.py — Redis cache for BugBuddy.

Three TTL tiers:
  bb:scrape:<KEY>          10 min  (Jira issue content)
  bb:rag:<sha256>           1 hr   (org terminology glossary)
  bb:llm:<provider:model:key:sha256>  24 hr  (LLM results)

All values are gzip+JSON encoded. If Redis is down the app continues
unaffected — every call degrades silently to a cache miss.

Env vars: REDIS_URL, CACHE_TTL_SCRAPE, CACHE_TTL_RAG, CACHE_TTL_LLM
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

# TODO: consider using a hash ring if we ever shard across multiple Redis nodes
_REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_TTL_SCRAPE  = int(os.getenv("CACHE_TTL_SCRAPE", "600"))
_TTL_RAG     = int(os.getenv("CACHE_TTL_RAG", "3600"))
_TTL_LLM     = int(os.getenv("CACHE_TTL_LLM", "86400"))

# Key prefixes
_PFX_SCRAPE = "bb:scrape:"
_PFX_RAG    = "bb:rag:"
_PFX_LLM    = "bb:llm:"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pack(value: Any) -> bytes:
    return gzip.compress(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def _unpack(raw: bytes) -> Any:
    return json.loads(gzip.decompress(raw).decode("utf-8"))


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------

class BugBuddyCache:
    """Thin Redis wrapper with three named tiers for BugBuddy data."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._url = redis_url or _REDIS_URL
        self._client = None
        self._connect()

    def _connect(self) -> None:
        try:
            import redis  # noqa: PLC0415
            self._client = redis.Redis.from_url(
                self._url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=False,
            )
            self._client.ping()
            log.info("BugBuddyCache: connected to %s", self._url)
        except Exception as exc:
            log.warning("BugBuddyCache: Redis unavailable (%s) — no caching", exc)
            self._client = None

    @property
    def available(self) -> bool:
        """True if Redis is reachable."""
        return self._client is not None

    # ------------------------------------------------------------------
    # Internal get / set with graceful degradation
    # ------------------------------------------------------------------

    def _get(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            raw = self._client.get(key)
            return _unpack(raw) if raw is not None else None
        except Exception as exc:
            log.debug("Cache GET error (%s) for key %s", exc, key)
            return None

    def _set(self, key: str, value: Any, ttl: int) -> None:
        if not self._client:
            return
        try:
            self._client.setex(key, ttl, _pack(value))
        except Exception as exc:
            log.debug("Cache SET error (%s) for key %s", exc, key)

    def _invalidate(self, key: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete(key)
        except Exception as exc:
            log.debug("Cache DEL error (%s) for key %s", exc, key)

    # --- Jira scrape tier ---

    def _scrape_key(self, issue_key: str) -> str:
        return _PFX_SCRAPE + issue_key.upper()

    def get_scrape(self, issue_key: str) -> dict | None:
        """Return cached scrape dict for *issue_key*, or None on miss."""
        return self._get(self._scrape_key(issue_key))

    def set_scrape(self, issue_key: str, data: dict) -> None:
        """Store scrape dict for *issue_key*."""
        self._set(self._scrape_key(issue_key), data, _TTL_SCRAPE)

    def invalidate_scrape(self, issue_key: str) -> None:
        """Force-evict the scrape cache for *issue_key*."""
        self._invalidate(self._scrape_key(issue_key))

    # --- RAG glossary tier ---

    def _rag_key(self, text: str) -> str:
        return _PFX_RAG + _sha256(text[:4000])   # only first 4K is sent to RAG

    def get_rag(self, full_text: str) -> str | None:
        """Return cached RAG glossary string, or None on miss."""
        return self._get(self._rag_key(full_text))

    def set_rag(self, full_text: str, glossary: str) -> None:
        """Store RAG glossary string."""
        self._set(self._rag_key(full_text), glossary, _TTL_RAG)

    # --- LLM result tier ---

    def _llm_key(self, provider: str, model: str, issue_key: str, full_text: str) -> str:
        content_hash = _sha256(full_text)
        return _PFX_LLM + f"{provider}:{model}:{issue_key.upper()}:{content_hash}"

    def get_llm(self, provider: str, model: str, issue_key: str, full_text: str) -> list | None:
        """Return cached LLM result list, or None on miss."""
        return self._get(self._llm_key(provider, model, issue_key, full_text))

    def set_llm(self, provider: str, model: str, issue_key: str,
                full_text: str, result: list) -> None:
        """Store LLM result list."""
        self._set(self._llm_key(provider, model, issue_key, full_text), result, _TTL_LLM)

    def invalidate_llm(self, provider: str, model: str,
                       issue_key: str, full_text: str) -> None:
        """Force-evict a specific LLM result from cache."""
        self._invalidate(self._llm_key(provider, model, issue_key, full_text))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return basic cache statistics (key counts per namespace)."""
        if not self._client:
            return {"available": False}
        try:
            scrape_count = len(self._client.keys(_PFX_SCRAPE + "*"))
            rag_count    = len(self._client.keys(_PFX_RAG    + "*"))
            llm_count    = len(self._client.keys(_PFX_LLM    + "*"))
            return {
                "available":     True,
                "scrape_cached": scrape_count,
                "rag_cached":    rag_count,
                "llm_cached":    llm_count,
            }
        except Exception:
            return {"available": False}

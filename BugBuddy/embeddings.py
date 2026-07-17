"""
embeddings.py — semantic memory for BugBuddy.

Stores past analyses in ChromaDB so we can find similar bugs and inject
their test cases as few-shot examples into the LLM prompt.

Supported embedding backends (EMBED_PROVIDER env var):
  sentence  — all-MiniLM-L6-v2 via sentence-transformers (default, no key needed)
  openai    — text-embedding-3-small
  mock      — MD5-derived unit vectors for tests

ChromaDB is embedded/local — no separate server. Data persists in CHROMA_PERSIST_DIR.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_CHROMA_DIR     = os.getenv("CHROMA_PERSIST_DIR", str(Path(__file__).parent / "chroma_store"))
_EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "sentence")
_EMBED_MODEL    = os.getenv("EMBED_MODEL", "text-embedding-3-small")
_OPENAI_KEY     = os.getenv("OPENAI_API_KEY", "")
_COLLECTION     = "bugbuddy_analyses"
_SIM_THRESHOLD  = float(os.getenv("EMBED_SIM_THRESHOLD", "0.92"))
_TOP_K_DEFAULT  = int(os.getenv("EMBED_TOP_K", "3"))
_MAX_EMBED_CHARS = 8_000

# TODO: try matryoshka embeddings once sentence-transformers 3.x is stable


def _embed_openai(texts: list[str]) -> list[list[float]]:
    import openai  # noqa: PLC0415
    client = openai.OpenAI(api_key=_OPENAI_KEY)
    response = client.embeddings.create(
        input=[t[:_MAX_EMBED_CHARS] for t in texts],
        model=_EMBED_MODEL,
    )
    return [item.embedding for item in response.data]


def _embed_sentence(texts: list[str]) -> list[list[float]]:
    """Local embeddings via sentence-transformers. Downloads the model on first run (~80MB)."""
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    except ImportError:
        import subprocess, sys  # noqa: PLC0415
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                                "sentence-transformers", "-q"])
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vecs  = model.encode([t[:_MAX_EMBED_CHARS] for t in texts],
                          normalize_embeddings=True)
    return vecs.tolist()


def _embed_mock(texts: list[str]) -> list[list[float]]:
    import hashlib, math  # noqa: PLC0415
    results = []
    for text in texts:
        digest = hashlib.md5(text.encode()).hexdigest()
        # 16-dim vector from MD5 bytes, normalised
        raw = [int(digest[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        norm = math.sqrt(sum(x**2 for x in raw))
        results.append([x / norm for x in raw])
    return results


def _embed(texts: list[str]) -> list[list[float]]:
    """Dispatch to the configured embedding provider."""
    provider = _EMBED_PROVIDER.lower()
    if provider == "openai":
        return _embed_openai(texts)
    if provider == "sentence":
        return _embed_sentence(texts)
    return _embed_mock(texts)


# ---------------------------------------------------------------------------
# SemanticMemory
# ---------------------------------------------------------------------------

class SemanticMemory:
    """ChromaDB vector store for BugBuddy. Stores past analyses, retrieves similar ones."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._dir = persist_dir or _CHROMA_DIR
        self._client     = None
        self._collection = None
        self._connect()

    def _connect(self) -> None:
        try:
            import chromadb  # noqa: PLC0415
            self._client = chromadb.PersistentClient(path=self._dir)
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION,
                metadata={"hnsw:space": "cosine"},  # cosine similarity
            )
            log.info("SemanticMemory: ChromaDB ready at %s (%d documents)",
                     self._dir, self._collection.count())
        except ImportError:
            log.warning("SemanticMemory: chromadb not installed — "
                        "run: pip install chromadb")
        except Exception as exc:
            log.warning("SemanticMemory: ChromaDB init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self._collection is not None

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(
        self,
        issue_key: str,
        text: str,
        test_cases: list[dict],
        metadata: dict | None = None,
    ) -> bool:
        """Embed the issue and store its test cases. Overwrites existing entry for the same key."""
        if not self.available:
            return False
        try:
            embed_text = self._make_embed_text(issue_key, text)

            # Check for near-duplicate
            existing = self._collection.get(ids=[issue_key])
            if existing["ids"]:
                log.debug("SemanticMemory: updating existing entry for %s", issue_key)
                self._collection.delete(ids=[issue_key])

            vec = _embed([embed_text])[0]
            meta = {
                "issue_key":  issue_key,
                "tc_count":   len(test_cases),
                **(metadata or {}),
            }
            self._collection.add(
                ids=[issue_key],
                embeddings=[vec],
                documents=[embed_text],
                metadatas=[meta],
            )
            # Store test cases as a side-car JSON file (ChromaDB metadata has size limits)
            self._write_tc_file(issue_key, test_cases)
            log.info("SemanticMemory: stored %d test cases for %s", len(test_cases), issue_key)
            return True
        except Exception as exc:
            log.warning("SemanticMemory store error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve_similar(self, text: str, top_k: int = _TOP_K_DEFAULT,
                         min_similarity: float = 0.5) -> list[dict]:
        """Return top-K past analyses ranked by cosine similarity to *text*.

        Items below min_similarity are filtered out. ChromaDB distance = 1 - similarity.
        """
        if not self.available:
            return []
        try:
            count = self._collection.count()
            if count == 0:
                return []

            vec = _embed([text[:_MAX_EMBED_CHARS]])[0]
            results = self._collection.query(
                query_embeddings=[vec],
                n_results=min(top_k, count),
                include=["metadatas", "distances"],
            )

            hits = []
            ids        = results["ids"][0]
            distances  = results["distances"][0]
            # ChromaDB cosine distance = 1 - cosine_similarity
            for issue_key, dist in zip(ids, distances):
                similarity = round(1.0 - dist, 4)
                if similarity < min_similarity:
                    continue
                tcs = self._read_tc_file(issue_key)
                if tcs:
                    hits.append({
                        "issue_key":  issue_key,
                        "similarity": similarity,
                        "test_cases": tcs,
                    })

            return sorted(hits, key=lambda x: x["similarity"], reverse=True)
        except Exception as exc:
            log.warning("SemanticMemory retrieve error: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Few-shot prompt builder
    # ------------------------------------------------------------------

    def build_fewshot_block(self, text: str, top_k: int = 2) -> str:
        """Return a formatted few-shot examples block for injection into the prompt.

        If no similar past analyses exist, returns an empty string so the
        caller's prompt is unchanged.
        """
        similar = self.retrieve_similar(text, top_k=top_k)
        if not similar:
            return ""

        lines = [
            "\n\n--- FEW-SHOT EXAMPLES (from similar past analyses) ---",
            "The following examples are test cases generated for similar bugs.",
            "Use them as a style reference — do NOT copy them verbatim.\n",
        ]
        for ex in similar:
            lines.append(
                f"[Past issue: {ex['issue_key']} | similarity: {ex['similarity']:.0%}]"
            )
            for tc in ex["test_cases"][:2]:   # show max 2 TCs per example
                lines.append(json.dumps(tc, indent=2))
            lines.append("")
        lines.append("--- END FEW-SHOT EXAMPLES ---")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        if not self.available:
            return {"available": False}
        try:
            return {
                "available":    True,
                "stored_issues": self._collection.count(),
                "persist_dir":   self._dir,
                "embed_provider": _EMBED_PROVIDER,
            }
        except Exception:
            return {"available": False}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_embed_text(self, issue_key: str, text: str) -> str:
        """Concatenate key + first N chars of text for embedding."""
        return f"{issue_key}: {text[:_MAX_EMBED_CHARS]}"

    def _tc_path(self, issue_key: str) -> Path:
        d = Path(self._dir) / "testcases"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{issue_key.replace('/', '_')}.json"

    def _write_tc_file(self, issue_key: str, test_cases: list[dict]) -> None:
        try:
            self._tc_path(issue_key).write_text(
                json.dumps(test_cases, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            log.warning("SemanticMemory: cannot write TC file: %s", exc)

    def _read_tc_file(self, issue_key: str) -> list[dict]:
        path = self._tc_path(issue_key)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

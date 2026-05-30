"""
org_rag.py
----------
Lightweight RAG (Retrieval-Augmented Generation) step that queries the
NetApp internal LLM proxy to extract organisation-specific terminology from
a Jira issue *before* the main test-gap analysis call.

Flow
----
  1. Jira text (first N chars) is sent to the knowledge proxy.
  2. The proxy explains any NetApp-internal terms, components, and acronyms
     it finds (it has access to internal docs / is a NetApp-tuned model).
  3. The returned glossary is injected into the main analysis system prompt
     so the external / generic LLM understands the org context.

This never raises — a failed knowledge look-up is silently skipped so the
main analysis always completes.

Configuration (env vars)
------------------------
  ORG_KNOWLEDGE_URL    Base URL of the knowledge proxy
                       (default: https://llm-proxy-web.ai.openeng.netapp.com)
  ORG_KNOWLEDGE_MODEL  Model to use on the knowledge proxy  (default: o1)
  ORG_KNOWLEDGE_KEY    API key  (or pass explicitly; leave blank to skip)
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Defaults  –  can be overridden via env vars
# ---------------------------------------------------------------------------

ORG_KNOWLEDGE_URL   = os.getenv(
    "ORG_KNOWLEDGE_URL",
    "https://llm-proxy-web.ai.openeng.netapp.com",
)
ORG_KNOWLEDGE_MODEL = os.getenv("ORG_KNOWLEDGE_MODEL", "o1")
ORG_KNOWLEDGE_KEY   = os.getenv("ORG_KNOWLEDGE_KEY", "")

# Only the first N chars of the Jira text are sent to the knowledge proxy —
# enough to identify all the org-specific terms without inflating cost/latency.
_SAMPLE_CHARS = 4000

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_KNOWLEDGE_PROMPT = """\
You are a NetApp internal technical assistant with expert knowledge of ONTAP,
StorageGRID, Element OS, cloud storage, and all NetApp internal tools,
infrastructure, release naming, and engineering processes.

Given the Jira bug report excerpt below, identify every NetApp-specific term,
subsystem, component, acronym, release codename, internal tool name, or
concept that appears.  For each item, write exactly one concise line:

  • TERM: plain-English explanation (one sentence, ≤20 words)

Skip generic programming / QA terms (JSON, REST, regression, etc.).
Focus only on NetApp-proprietary or NetApp-internal jargon.
If no NetApp-specific terms are found, respond with exactly: (none)

Jira excerpt:
{excerpt}
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_org_knowledge(full_text: str, api_key: str | None = None) -> str:
    """Query the internal knowledge proxy and return a glossary string.

    Parameters
    ----------
    full_text : The full Jira issue text produced by JiraScrubber.full_text().
    api_key   : API key for the knowledge proxy.  Falls back to the
                ORG_KNOWLEDGE_KEY env var.  Returns '' if neither is set.

    Returns
    -------
    A bullet-list string explaining org-specific terms, or '' if the proxy is
    unconfigured, the response is empty, or any error occurs.
    """
    key = api_key or ORG_KNOWLEDGE_KEY
    if not key:
        return ""

    try:
        import openai  # noqa: PLC0415
        import httpx   # noqa: PLC0415

        client = openai.OpenAI(
            api_key=key,
            base_url=ORG_KNOWLEDGE_URL,
            # Corporate network uses a self-signed TLS certificate
            http_client=httpx.Client(verify=False),
        )

        excerpt = full_text[:_SAMPLE_CHARS]

        # o1 models do not support a system role — use user only
        response = client.chat.completions.create(
            model=ORG_KNOWLEDGE_MODEL,
            messages=[{
                "role": "user",
                "content": _KNOWLEDGE_PROMPT.format(excerpt=excerpt),
            }],
            temperature=0,
            user=_get_username(),
        )

        result = (response.choices[0].message.content or "").strip()
        # If the model signalled "no terms found", treat as empty
        if result.lower().startswith("(none)"):
            return ""
        return result

    except Exception as exc:  # never let this break the main analysis
        return f"(org knowledge lookup skipped: {exc})"


def get_config() -> dict:
    """Return the current effective configuration (safe to expose to GUI)."""
    return {
        "url":         ORG_KNOWLEDGE_URL,
        "model":       ORG_KNOWLEDGE_MODEL,
        "key_env":     "ORG_KNOWLEDGE_KEY",
        "key_hint":    "Key from llm-proxy-web portal",
        "configured":  bool(ORG_KNOWLEDGE_KEY),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_username() -> str:
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return "unknown"

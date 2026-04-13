"""
llm_agent.py
------------
Takes the full text content of a Jira issue (from jira_scrubber.py) and
sends it to an LLM to generate test gap analysis.

Supported providers (LLM_PROVIDER env var or constructor argument):
  openai    – OpenAI GPT models              (pip install openai)
  netapp    – NetApp proxy → gpt-4.1         (pip install openai, internal network)
  anthropic – Anthropic Claude models        (pip install anthropic)
  gemini    – Google Gemini models           (pip install google-generativeai)
  mock      – Deterministic dummy data       (no API key needed)

Each provider exposes a curated list of models. The user can override the
model by passing model= or setting LLM_MODEL.
"""

from __future__ import annotations

import getpass
import json
import os
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Chunking constants  –  split oversized full_text so no data is ever lost
# ---------------------------------------------------------------------------
# Each chunk is sent to the LLM independently and results are merged.
# 600K chars ≈ 150K tokens, leaves plenty of room for the system prompt
# (~2K tokens) and the model's JSON response (~4K tokens).
_CHUNK_SIZE_CHARS    = 600_000
_CHUNK_OVERLAP_CHARS = 3_000   # repeat end of previous chunk at start of next


# ---------------------------------------------------------------------------
# Provider catalog  –  exported so GUI / CLI can build dropdowns from this
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, dict] = {
    "openai": {
        "label": "OpenAI GPT",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o1",
            "o1-mini",
        ],
        "key_env":  "OPENAI_API_KEY",
        "key_hint": "sk-...",
        "base_url": None,
    },
    "netapp": {
        "label": "NetApp LLM Proxy (internal)",
        "models": [
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
        ],
        "key_env":  "NETAPP_LLM_KEY",
        "key_hint": "your-netapp-llm-key",
        "base_url": "https://llm-proxy-api.ai.eng.netapp.com",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "key_env":  "ANTHROPIC_API_KEY",
        "key_hint": "sk-ant-...",
        "base_url": None,
    },
    "gemini": {
        "label": "Google Gemini",
        "models": [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "key_env":  "GOOGLE_API_KEY",
        "key_hint": "AIza...",
        "base_url": None,
    },
    "mock": {
        "label": "Mock (no key needed)",
        "models": ["mock"],
        "key_env":  "",
        "key_hint": "",
        "base_url": None,
    },
}


# ---------------------------------------------------------------------------
# Org context loader  (reads org_context.yaml next to this file)
# ---------------------------------------------------------------------------

_ORG_CONTEXT_PATH = Path(__file__).parent / "org_context.yaml"
_org_context_cache: str | None = None


def load_org_context(force_reload: bool = False) -> str:
    """Return a formatted string built from org_context.yaml, or '' if missing.

    The result is cached after first load.  Pass force_reload=True to re-read
    the file (e.g. after the user edits it via the GUI).
    """
    global _org_context_cache
    if _org_context_cache is not None and not force_reload:
        return _org_context_cache
    if not _ORG_CONTEXT_PATH.exists():
        _org_context_cache = ""
        return ""
    try:
        import yaml  # pip install pyyaml
        with open(_ORG_CONTEXT_PATH, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        parts: list[str] = []

        # Product overview
        product = data.get("product", {})
        if product.get("name"):
            parts.append(
                f"PRODUCT: {product['name']}\n"
                + (product.get("description", "").strip())
            )

        # Jira project keys
        projects = data.get("jira_projects", {})
        if projects:
            lines = ["JIRA PROJECTS:"]
            for k, v in projects.items():
                lines.append(f"  {k}: {v}")
            parts.append("\n".join(lines))

        # Components
        components = data.get("components", {})
        if components:
            lines = ["INTERNAL COMPONENTS / SUBSYSTEMS:"]
            for name, info in components.items():
                if isinstance(info, dict):
                    full = info.get("full_name", "")
                    desc = info.get("description", "").strip()
                    lines.append(f"  {name}" + (f" ({full})" if full else "") + f": {desc}")
                else:
                    lines.append(f"  {name}: {info}")
            parts.append("\n".join(lines))

        # Acronyms
        acronyms = data.get("acronyms", {})
        if acronyms:
            lines = ["ACRONYMS / ABBREVIATIONS:"]
            for k, v in acronyms.items():
                lines.append(f"  {k}: {v}")
            parts.append("\n".join(lines))

        # Test environment
        test_env = data.get("test_environment", {})
        if test_env:
            lines = ["TEST ENVIRONMENT:"]
            for section, items in test_env.items():
                lines.append(f"  {section}:")
                for item in (items if isinstance(items, list) else [items]):
                    lines.append(f"    - {item}")
            parts.append("\n".join(lines))

        # Architecture notes (free text)
        arch = data.get("architecture_notes", "")
        if isinstance(arch, str) and arch.strip():
            parts.append("ARCHITECTURE NOTES:\n" + arch.strip())

        _org_context_cache = "\n\n".join(parts)
    except Exception as exc:  # never break the analysis for a bad context file
        _org_context_cache = f"(org_context.yaml could not be loaded: {exc})"
    return _org_context_cache


def _build_system_prompt(org_knowledge: str = "") -> str:
    """Return the system prompt enriched with org context (YAML + live knowledge)."""
    ctx = load_org_context()   # static YAML glossary (fallback / base)
    sections: list[str] = [_SYSTEM_PROMPT_BASE]

    if ctx:
        sections.append(
            "\n\n--- ORGANIZATION-SPECIFIC CONTEXT (static) ---\n"
            "The following internal terminology, components, and architecture notes\n"
            "are specific to this organization. Use them to interpret the Jira content.\n\n"
            + ctx +
            "\n--- END STATIC CONTEXT ---"
        )

    if org_knowledge and not org_knowledge.startswith("(org knowledge lookup skipped"):
        sections.append(
            "\n\n--- ORGANIZATION TERMINOLOGY (from internal knowledge proxy) ---\n"
            "The following terms were identified in this specific Jira issue and\n"
            "explained using NetApp's internal knowledge base:\n\n"
            + org_knowledge +
            "\n--- END KNOWLEDGE CONTEXT ---"
        )

    return "".join(sections)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = """\
You are a senior QA engineer specialising in test gap analysis.
You will be given the full content of a Jira bug report — its description,
comments, and any attachment text.

Your job is to identify what test design was MISSING before this bug was filed.
For each gap you find, produce a concrete test case that, had it existed in the
test suite before the bug was reported, would have caught the defect and
prevented it from reaching the field.

Focus on:
  - Boundary conditions and edge cases not covered
  - Mixed-state or mixed-version scenarios
  - Negative / failure-path scenarios
  - Interaction between components or configuration combinations
  - Any explicit test steps mentioned in comments that were not performed

Return ONLY valid JSON – a list of test case objects. Each object must have
exactly these keys:
  tc_number     : string, e.g. "TC-001"
  title         : short descriptive title of the test scenario
  gap_reason    : one sentence explaining why this test was missing / not run
  preconditions : any required setup or state before the test
  steps         : list of strings, each a plain action step (no leading numbers)
  expected      : expected result that would have revealed the defect
  test_type     : one of: Functional, Regression, Negative, Performance, Boundary

Do not include any text outside the JSON array.
"""

_USER_PROMPT_TEMPLATE = """\
Below is the full content of Jira issue {key}.

Analyse what test design steps were MISSING that allowed this defect to be
filed. Generate test cases that, had they been executed before the bug was
reported, would have caught it and prevented it from reaching the field.

{full_text}
"""

_USER_PROMPT_TEMPLATE_CHUNK = """\
Below is PART {chunk_num} of {total_chunks} of Jira issue {key}.

This is a large issue — the content has been split into {total_chunks} parts
for analysis. Analyse only the content PROVIDED in this part and identify
missing test cases that would have caught defects described here.
Do not mention that this is a partial analysis in your output.

{full_text}
"""


# ---------------------------------------------------------------------------
# LLM provider implementations
# ---------------------------------------------------------------------------

def _call_openai(prompt: str, issue_key: str, model: str, api_key: str,
                 base_url: str | None = None, user: str | None = None,
                 verify_ssl: bool = True, org_knowledge: str = "") -> str:
    import openai, httpx  # noqa: PLC0415
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    if not verify_ssl:
        kwargs["http_client"] = httpx.Client(verify=False)
    client = openai.OpenAI(**kwargs)
    call_kwargs: dict = dict(
        model=model,
        messages=[
            {"role": "system", "content": _build_system_prompt(org_knowledge)},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,
    )
    if user:
        call_kwargs["user"] = user
    response = client.chat.completions.create(**call_kwargs)
    return response.choices[0].message.content


def _call_anthropic(prompt: str, issue_key: str, model: str, api_key: str,
                    org_knowledge: str = "") -> str:
    import anthropic  # noqa: PLC0415
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_build_system_prompt(org_knowledge),
        messages=[{
            "role": "user",
            "content": prompt,
        }],
    )
    return message.content[0].text


def _call_gemini(prompt: str, issue_key: str, model: str, api_key: str,
                 org_knowledge: str = "") -> str:
    import google.generativeai as genai  # noqa: PLC0415
    genai.configure(api_key=api_key)
    llm = genai.GenerativeModel(
        model_name=model,
        system_instruction=_build_system_prompt(org_knowledge),
    )
    response = llm.generate_content(
        prompt,
        generation_config={"temperature": 0.2},
    )
    return response.text

def _call_mock(prompt: str, issue_key: str, **_: Any) -> str:
    """Returns deterministic dummy test cases – useful for UI development."""
    return json.dumps([
        {
            "tc_number":     "TC-001",
            "title":         f"Verify core functionality for {issue_key}",
            "gap_reason":    "The happy-path scenario was not covered in the existing test suite.",
            "preconditions": "System is running; user has valid credentials.",
            "steps":         ["1. Log in as a valid user.",
                              "2. Navigate to the affected feature.",
                              "3. Reproduce the steps described in the Jira."],
            "expected":      "No error occurs; expected output is returned.",
            "test_type":     "Regression",
        },
        {
            "tc_number":     "TC-002",
            "title":         f"Verify negative path for {issue_key}",
            "gap_reason":    "Boundary and invalid-input scenarios were not tested before filing.",
            "preconditions": "System is running; invalid input is prepared.",
            "steps":         ["1. Log in as a valid user.",
                              "2. Provide invalid or boundary input.",
                              "3. Observe system behaviour."],
            "expected":      "System handles invalid input gracefully with a clear error message.",
            "test_type":     "Negative",
        },
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class LLMAgent:
    """Generates test gap analysis from Jira issue content via an LLM.

    Parameters
    ----------
    provider : "openai" | "netapp" | "anthropic" | "gemini" | "mock"
    api_key  : API key for the chosen provider. Falls back to the relevant
               env var (OPENAI_API_KEY, NETAPP_LLM_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY).
    model    : Model name. Defaults to the first model in PROVIDERS[provider]['models'].
    """

    def __init__(
        self,
        provider: str = "mock",
        api_key: str | None = None,
        model: str | None = None,
        org_knowledge_key: str | None = None,
    ) -> None:
        self.provider = provider.lower()
        if self.provider not in PROVIDERS:
            raise ValueError(
                f"Unknown provider {self.provider!r}. "
                f"Choose from: {', '.join(PROVIDERS)}"
            )
        key_env = PROVIDERS[self.provider].get("key_env", "")
        self.api_key = api_key or (os.getenv(key_env, "") if key_env else "")
        default_model = PROVIDERS[self.provider]["models"][0]
        self.model = model or default_model
        # Key for the internal knowledge proxy (llm-proxy-web); falls back to env var
        from org_rag import ORG_KNOWLEDGE_KEY  # noqa: PLC0415
        self.org_knowledge_key = org_knowledge_key or ORG_KNOWLEDGE_KEY or None

    def generate_test_cases(self, scraped_issue: dict, scrubber=None) -> list[dict]:
        """Generate test cases for a scraped issue dict (from JiraScrubber.scrub()).

        If the issue content is larger than _CHUNK_SIZE_CHARS the text is split
        into overlapping chunks, each analysed independently, and the results
        are merged and deduplicated — so NO content is ever discarded.

        Parameters
        ----------
        scraped_issue : dict returned by JiraScrubber.scrub()
        scrubber      : JiraScrubber instance (used to call full_text(); if None,
                        the method builds a simple text representation itself).
        """
        if scrubber is not None:
            full_text = scrubber.full_text(scraped_issue)
        else:
            full_text = self._simple_text(scraped_issue)

        issue_key = scraped_issue.get("key", "UNKNOWN")

        # --- Step 1: fetch org-specific term definitions (optional, never fatal) ---
        org_knowledge = ""
        if self.org_knowledge_key and self.provider != "mock":
            from org_rag import fetch_org_knowledge  # noqa: PLC0415
            org_knowledge = fetch_org_knowledge(full_text, self.org_knowledge_key)

        # --- Step 2: split if needed, analyse, merge ---
        chunks = self._split_chunks(full_text)
        all_cases: list[list[dict]] = []
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                prompt = _USER_PROMPT_TEMPLATE_CHUNK.format(
                    key=issue_key, chunk_num=i, total_chunks=len(chunks),
                    full_text=chunk
                )
            else:
                prompt = _USER_PROMPT_TEMPLATE.format(key=issue_key, full_text=chunk)
            raw = self._call_provider(prompt, issue_key, org_knowledge)
            all_cases.append(self._parse(raw))

        return self._merge_test_cases(all_cases)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _call_provider(self, prompt: str, issue_key: str, org_knowledge: str) -> str:
        """Dispatch a formatted prompt string to the configured LLM provider."""
        if self.provider in ("openai", "netapp"):
            base_url  = PROVIDERS[self.provider].get("base_url")
            user      = getpass.getuser() if self.provider == "netapp" else None
            verify_ssl = self.provider != "netapp"
            return _call_openai(prompt, issue_key, self.model, self.api_key,
                                base_url=base_url, user=user, verify_ssl=verify_ssl,
                                org_knowledge=org_knowledge)
        if self.provider == "anthropic":
            return _call_anthropic(prompt, issue_key, self.model, self.api_key,
                                   org_knowledge=org_knowledge)
        if self.provider == "gemini":
            return _call_gemini(prompt, issue_key, self.model, self.api_key,
                                org_knowledge=org_knowledge)
        if self.provider == "mock":
            return _call_mock(prompt, issue_key)
        raise ValueError(f"Unknown LLM provider: {self.provider!r}")

    @staticmethod
    def _split_chunks(text: str) -> list[str]:
        """Split *text* into ≤_CHUNK_SIZE_CHARS chunks with a small overlap.

        The overlap ensures that context spanning a chunk boundary is seen by
        both the preceding and following chunk's LLM call.
        """
        if len(text) <= _CHUNK_SIZE_CHARS:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + _CHUNK_SIZE_CHARS, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - _CHUNK_OVERLAP_CHARS
        return chunks

    @staticmethod
    def _merge_test_cases(all_cases: list[list[dict]]) -> list[dict]:
        """Merge test cases from multiple chunks, dedup by title similarity.

        Two test cases are considered duplicates when their titles share ≥70%
        of words (Jaccard similarity on lowercased word sets).
        """
        def _jaccard(a: str, b: str) -> float:
            wa = set(re.sub(r'[^\w\s]', '', a.lower()).split())
            wb = set(re.sub(r'[^\w\s]', '', b.lower()).split())
            if not wa and not wb:
                return 1.0
            if not wa or not wb:
                return 0.0
            return len(wa & wb) / len(wa | wb)

        merged: list[dict] = []
        seen_titles: list[str] = []
        for cases in all_cases:
            for tc in cases:
                title = tc.get("title", "")
                if any(_jaccard(title, s) >= 0.70 for s in seen_titles):
                    continue  # close enough duplicate — skip
                seen_titles.append(title)
                merged.append(tc)

        # Renumber sequentially
        for i, tc in enumerate(merged, 1):
            tc["tc_number"] = f"TC-{i:03d}"
        return merged

    def _simple_text(self, scraped: dict) -> str:
        parts = [
            f"Issue: {scraped.get('key', '')}",
            f"Summary: {scraped.get('summary', '')}",
            f"Description:\n{scraped.get('description', '')}",
        ]
        for i, c in enumerate(scraped.get("comments", []), 1):
            parts.append(f"Comment {i}:\n{c['body']}")
        for a in scraped.get("attachments", []):
            parts.append(f"Attachment {a['filename']}:\n{a['content']}")
        return "\n\n".join(parts)

    def _parse(self, raw: str) -> list[dict]:
        """Extract JSON array from LLM response (handles markdown code fences)."""
        # Strip ```json ... ``` fences if present
        raw = raw.strip()
        match = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

        # Sometimes the model wraps the array in an object
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Last resort: find the first [ ... ] block
            m = re.search(r'\[.*\]', raw, re.DOTALL)
            if m:
                data = json.loads(m.group())
            else:
                return [{"tc_number": "TC-ERR", "title": "Parse error",
                         "preconditions": "", "steps": [raw],
                         "expected": "", "test_type": "Unknown"}]

        if isinstance(data, dict):
            # e.g. {"test_cases": [...]}
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break

        if not isinstance(data, list):
            return []

        # Normalise keys — include gap_reason
        result = []
        for i, tc in enumerate(data, 1):
            result.append({
                "tc_number":     tc.get("tc_number", f"TC-{i:03d}"),
                "title":         tc.get("title", ""),
                "gap_reason":    tc.get("gap_reason", ""),
                "preconditions": tc.get("preconditions", ""),
                "steps":         tc.get("steps", []),
                "expected":      tc.get("expected", ""),
                "test_type":     tc.get("test_type", "Functional"),
            })
        return result

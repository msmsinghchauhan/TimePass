# guardrails.py — sanitise Jira text before it hits an external LLM.
#
# Covers three things:
#   - PII redaction (emails, IPs, phones, CC numbers)
#   - Prompt injection detection
#   - Hard length ceiling for external providers
#
# Internal providers (netapp proxy) skip PII redaction since data stays on-prem.
# Set skip_pii=True if you want to bypass redaction for a specific call.

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
_IPV4_RE  = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CC_RE    = re.compile(r"\b(?:\d[ -]?){13,16}\b")

# FIXME: these injection patterns catch obvious cases but a determined attacker
# could encode payloads in base64 or unicode lookalikes — good enough for now
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"disregard\s+(the\s+)?system\s+prompt", re.I),
    re.compile(r"you\s+are\s+now\s+a?\s*(different|new)?\s*(AI|assistant|bot)", re.I),
    re.compile(r"do\s+not\s+follow\s+your\s+(original\s+)?instructions", re.I),
    re.compile(r"(override|bypass)\s+(system|safety|guardrail)", re.I),
    re.compile(r"<\|system\|>|<\|user\|>|<\|assistant\|>"),   # special tokens
    re.compile(r"\[INST\]|\[/INST\]|\[SYS\]"),                 # Llama tokens
]

_MAX_EXTERNAL_CHARS = 2_000_000
_INTERNAL_PROVIDERS = {"netapp", "mock"}


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class GuardrailResult:
    text:           str
    blocked:        bool         = False
    reason:         str          = ""
    pii_redactions: int          = 0
    warnings:       list[str]    = field(default_factory=list)


# ---------------------------------------------------------------------------
# Guardrail engine
# ---------------------------------------------------------------------------

class InputGuardrail:
    """Validates and sanitises text before it is sent to an LLM provider."""

    def __init__(
        self,
        redact_pii: bool = True,
        max_chars: int = _MAX_EXTERNAL_CHARS,
    ) -> None:
        self._redact_pii = redact_pii
        self._max_chars  = max_chars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, text: str, provider: str = "openai") -> GuardrailResult:
        """Run all guardrail checks. Returns a GuardrailResult — inspect .blocked before using .text."""
        result = GuardrailResult(text=text)
        is_internal = provider.lower() in _INTERNAL_PROVIDERS

        # 1. Prompt injection detection (applies to all providers)
        injection = self._detect_injection(text)
        if injection:
            result.blocked = True
            result.reason  = f"Prompt injection pattern detected: {injection!r}"
            logger.warning("GUARDRAIL BLOCKED injection pattern in input for provider=%s", provider)
            return result

        if self._redact_pii and not is_internal:
            text, count = self._redact(text)
            result.pii_redactions = count
            if count:
                result.warnings.append(f"Redacted {count} PII item(s) before sending to {provider}")
                logger.info("Guardrail: redacted %d PII items for provider=%s", count, provider)

        if len(text) > self._max_chars:
            original_len = len(text)
            text = text[: self._max_chars]
            result.warnings.append(
                f"Input truncated from {original_len:,} to {self._max_chars:,} chars"
            )
            logger.warning("Guardrail: input truncated to %d chars", self._max_chars)

        result.text = text
        return result

    def scrub_pii(self, text: str) -> tuple[str, int]:
        """Convenience: just run PII redaction and return (clean_text, count)."""
        return self._redact(text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_injection(self, text: str) -> str | None:
        """Return the matched injection pattern string, or None if clean."""
        for pat in _INJECTION_PATTERNS:
            m = pat.search(text)
            if m:
                return m.group(0)
        return None

    def _redact(self, text: str) -> tuple[str, int]:
        """Replace PII patterns with typed placeholders."""
        count = 0

        def _sub(pattern: re.Pattern, placeholder: str, t: str) -> tuple[str, int]:
            matches = pattern.findall(t)
            return pattern.sub(placeholder, t), len(matches)

        text, n = _sub(_EMAIL_RE,  "[REDACTED-EMAIL]",  text); count += n
        text, n = _sub(_IPV4_RE,   "[REDACTED-IP]",     text); count += n
        text, n = _sub(_PHONE_RE,  "[REDACTED-PHONE]",  text); count += n
        text, n = _sub(_CC_RE,     "[REDACTED-CC]",     text); count += n

        return text, count


# ---------------------------------------------------------------------------
# Output guardrail
# ---------------------------------------------------------------------------

class OutputGuardrail:
    """Validates LLM output before it is returned to the caller.

    Catches cases where the LLM returns something that looks like a refusal
    or an error message instead of the expected JSON test cases.
    """

    _REFUSAL_PATTERNS = [
        re.compile(r"I('m| am) (sorry|unable|not able)", re.I),
        re.compile(r"I cannot (help|assist|provide)", re.I),
        re.compile(r"as an AI (language model|assistant)", re.I),
        re.compile(r"I don't have (access|the ability)", re.I),
        re.compile(r"content policy", re.I),
    ]

    def is_refusal(self, text: str) -> bool:
        """Return True if the LLM appears to have refused to answer."""
        stripped = text.strip()
        # If it starts with [ or { it's almost certainly JSON — not a refusal
        if stripped.startswith(("[", "{")):
            return False
        for pat in self._REFUSAL_PATTERNS:
            if pat.search(stripped[:300]):
                return True
        return False

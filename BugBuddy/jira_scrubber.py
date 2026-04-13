"""
jira_scrubber.py
----------------
Reads a single Jira issue and extracts:
  - Summary, description, issue metadata
  - All comments (cleaned of Jira markup)
  - Text content of all attachments (reuses BugBuddyExperiment helpers)

Returns a structured dict consumed by llm_agent.py.
"""

from __future__ import annotations

import io
import re
import zipfile
import tarfile
import gzip
from typing import Optional

from jira import JIRA
from striprtf.striprtf import rtf_to_text
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from openpyxl import load_workbook


# ---------------------------------------------------------------------------
# Markup helpers (ported from BugBuddyExperiment.py)
# ---------------------------------------------------------------------------

def _remove_color_tags(text: str) -> str:
    return re.sub(r'\{/?color[^}]*\}', '', text)


def _clean_jira_markup(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\{[^}]+\}', '', text)
    text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'\[([^\|]+)\|[^\]]+\]', r'\1', text)
    text = re.sub(r'h[1-6]\.\s*', '', text)
    text = re.sub(r'^\s*\*\s+', '- ', text, flags=re.MULTILINE)
    return text.strip()


def _read_attachment_bytes(raw_bytes: bytes, name: str) -> str:
    """Extract readable text from raw attachment bytes."""
    try:
        if name.endswith(".rtf") or raw_bytes[:5] == b'{\\rtf':
            return rtf_to_text(raw_bytes.decode("latin-1"))

        if name.endswith(".pdf") or raw_bytes[:4] == b'%PDF':
            return extract_pdf_text(io.BytesIO(raw_bytes))

        if name.endswith(".docx"):
            doc = Document(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        if name.endswith(".xlsx"):
            wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
            parts = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                parts.append(f"=== Sheet: {sheet} ===")
                for row in ws.iter_rows(values_only=True):
                    line = "\t".join(str(c) if c is not None else "" for c in row)
                    if line.strip():
                        parts.append(line)
            return "\n".join(parts)

        if name.endswith((".tar.bz2", ".tbz2")) or raw_bytes[:3] == b'BZh':
            with tarfile.open(fileobj=io.BytesIO(raw_bytes), mode="r:bz2") as tf:
                parts = []
                for m in tf.getmembers():
                    f = tf.extractfile(m)
                    if f:
                        parts.append(f"=== {m.name} ===\n{f.read().decode('utf-8', errors='replace')}")
                return "\n\n".join(parts)

        if zipfile.is_zipfile(io.BytesIO(raw_bytes)):
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                return "\n\n".join(
                    f"=== {n} ===\n{zf.read(n).decode('utf-8', errors='replace')}"
                    for n in zf.namelist()
                )

        if raw_bytes[:2] == b'\x1f\x8b':
            raw_bytes = gzip.decompress(raw_bytes)

        if tarfile.is_tarfile(io.BytesIO(raw_bytes)):
            with tarfile.open(fileobj=io.BytesIO(raw_bytes)) as tf:
                parts = []
                for m in tf.getmembers():
                    f = tf.extractfile(m)
                    if f:
                        parts.append(f"=== {m.name} ===\n{f.read().decode('utf-8', errors='replace')}")
                return "\n\n".join(parts)

        return raw_bytes.decode("utf-8", errors="replace")

    except Exception as exc:
        return f"[Could not read {name}: {exc}]"


# ---------------------------------------------------------------------------
# Scrubber
# ---------------------------------------------------------------------------

class JiraScrubber:
    """Reads a single Jira issue and returns all meaningful text content.

    Parameters
    ----------
    jira_client:
        An authenticated jira.JIRA instance.
    max_attachment_bytes:
        Skip attachments larger than this (default 5 MB) to avoid memory issues.
    """

    def __init__(self, jira_client: JIRA, max_attachment_bytes: int = 5 * 1024 * 1024) -> None:
        self._jira = jira_client
        self._max_bytes = max_attachment_bytes

    def _scrub_raw(self, issue_key: str) -> dict:
        """Internal: scrub a single issue key into a structured dict."""
        issue = self._jira.issue(
            issue_key,
            fields="summary,description,status,priority,assignee,reporter,"
                   "issuetype,fixVersions,customfield_21440,comment,attachment,parent,subtasks"
        )
        return self._parse_issue(issue)

    def _parse_issue(self, issue) -> dict:
        """Parse a raw Jira issue object into a structured dict."""
        f = issue.fields

        # --- description ---
        description = _clean_jira_markup(_remove_color_tags(f.description or ""))

        # --- comments ---
        comments = []
        if f.comment and f.comment.comments:
            for c in f.comment.comments:
                comments.append({
                    "author":  c.author.displayName if c.author else "Unknown",
                    "created": str(c.created)[:10],
                    "body":    _clean_jira_markup(_remove_color_tags(c.body or "")),
                })

        # --- attachments ---
        attachments = []
        for att in (f.attachment or []):
            if att.size > self._max_bytes:
                attachments.append({
                    "filename": att.filename,
                    "content":  f"[Skipped – file too large ({att.size} bytes)]",
                })
                continue
            raw = self._jira._session.get(att.content).content
            text = _read_attachment_bytes(raw, att.filename)
            attachments.append({"filename": att.filename, "content": text})

        # --- target release ---
        tr_field = getattr(f, "customfield_21440", None)
        target_release = tr_field.value if tr_field and hasattr(tr_field, "value") else (
            str(tr_field) if tr_field else ""
        )

        server = self._jira.server_info().get("baseUrl", "").rstrip("/")

        # --- parent key (if this is a subtask) ---
        # Read raw JSON directly — jira-python attribute access can silently fail
        raw_fields = issue.raw.get("fields", {}) if hasattr(issue, "raw") else {}
        raw_parent = raw_fields.get("parent") or {}
        parent_key = raw_parent.get("key") or None
        if not parent_key:
            # fallback to attribute access
            p = getattr(f, "parent", None)
            if p and getattr(p, "key", None):
                parent_key = p.key

        # --- subtask keys ---
        subtask_keys = []
        if hasattr(f, "subtasks") and f.subtasks:
            subtask_keys = [s.key for s in f.subtasks]

        return {
            "key":            issue.key,
            "url":            f"{server}/browse/{issue.key}",
            "summary":        f.summary or "",
            "description":    description,
            "issue_type":     f.issuetype.name if f.issuetype else "",
            "status":         f.status.name if f.status else "",
            "priority":       f.priority.name if f.priority else "",
            "assignee":       f.assignee.displayName if f.assignee else "Unassigned",
            "reporter":       f.reporter.displayName if f.reporter else "",
            "fix_versions":   [v.name for v in f.fixVersions] if f.fixVersions else [],
            "target_release": target_release,
            "comments":       comments,
            "attachments":    attachments,
            "parent_key":     parent_key,
            "subtask_keys":   subtask_keys,
        }

    # Per-comment body limit: keeps individual comments concise.
    # Long attachments (log files etc.) are NOT truncated here — the LLM
    # agent splits oversized full-texts into chunks so nothing is lost.
    _MAX_COMMENT_CHARS = 3_000

    def _trim(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n… [truncated, {len(text)-limit} chars omitted]"

    def scrub(self, issue_key: str) -> dict:
        """Fetch and return all text content for a single Jira issue."""
        return self._scrub_raw(issue_key)

    def scrub_with_parent(self, issue_key: str) -> dict:
        """Scrub a Jira issue and enrich it with its parent's full context."""
        scraped = self._scrub_raw(issue_key)
        parent_scraped = None

        if scraped.get("parent_key"):
            try:
                parent_scraped = self._scrub_raw(scraped["parent_key"])
            except Exception:
                pass  # parent fetch failure is non-fatal

        scraped["parent_scraped"] = parent_scraped
        return scraped

    def full_text(self, scraped: dict) -> str:
        """Flatten all text from a scrub() / scrub_with_parent() result into
        one string for the LLM.  Parent context is included first when present.
        Content is intelligently trimmed to stay within the model context limit.
        """
        parts = []

        # --- parent context block (prepended) ---
        parent = scraped.get("parent_scraped")
        if parent:
            parts.append(
                f"=== PARENT / MASTER JIRA: {parent['key']} ===\n"
                f"Summary: {parent['summary']}\n"
                f"Type: {parent['issue_type']}  Status: {parent['status']}  "
                f"Priority: {parent['priority']}"
            )
            parts.append("--- Parent Description ---\n" +
                         self._trim(parent["description"], 20_000))
            if parent["comments"]:
                parts.append("--- Parent Comments (most recent first) ---")
                for c in reversed(parent["comments"]):
                    parts.append(f"({c['author']}, {c['created']}):\n" +
                                 self._trim(c["body"], self._MAX_COMMENT_CHARS))
            if parent["attachments"]:
                parts.append("--- Parent Attachments ---")
                for a in parent["attachments"]:
                    parts.append(f"--- {a['filename']} ---\n{a['content']}")
            parts.append("=== END PARENT CONTEXT ===")

        # --- primary issue ---
        parts += [
            f"Issue: {scraped['key']}",
            f"Summary: {scraped['summary']}",
            f"Type: {scraped['issue_type']}  Status: {scraped['status']}  Priority: {scraped['priority']}",
            f"Assignee: {scraped['assignee']}  Reporter: {scraped['reporter']}",
            "",
            "=== Description ===",
            self._trim(scraped["description"], 20_000),
        ]
        if scraped["comments"]:
            parts.append("\n=== Comments (most recent first) ===")
            for c in reversed(scraped["comments"]):
                parts.append(f"({c['author']}, {c['created']}):\n" +
                             self._trim(c["body"], self._MAX_COMMENT_CHARS))
        if scraped["attachments"]:
            parts.append("\n=== Attachments ===")
            for a in scraped["attachments"]:
                parts.append(f"--- {a['filename']} ---\n{a['content']}")

        return "\n\n".join(parts)

"""
generate_project_doc.py
-----------------------
Generates the BugBuddy technical architecture and design review document.

Run:
    python generate_project_doc.py
    python generate_project_doc.py --pdf   # also convert to PDF via docx2pdf

Output: BugBuddy_Project_Architecture.docx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

OUTPUT_PATH = Path(__file__).parent / "BugBuddy_Project_Architecture.docx"

# --- colour palette ---
NAVY   = RGBColor(0x00, 0x2D, 0x62)
TEAL   = RGBColor(0x00, 0x7A, 0x87)
ORANGE = RGBColor(0xD4, 0x6B, 0x08)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
GREEN  = RGBColor(0x1A, 0x6B, 0x2A)
RED    = RGBColor(0xB5, 0x0E, 0x0E)
GREY   = RGBColor(0x40, 0x40, 0x40)
LGREY  = RGBColor(0xF5, 0xF5, 0xF5)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cell_bg(cell, hex6: str) -> None:
    tc = cell._tc
    pr = tc.get_or_add_tcPr()
    s  = OxmlElement("w:shd")
    s.set(qn("w:val"),   "clear")
    s.set(qn("w:color"), "auto")
    s.set(qn("w:fill"),  hex6)
    pr.append(s)


def h1(doc, text):
    p = doc.add_heading(text, 1)
    r = p.runs[0] if p.runs else p.add_run(text)
    r.font.color.rgb = NAVY
    r.font.bold = True


def h2(doc, text):
    p = doc.add_heading(text, 2)
    r = p.runs[0] if p.runs else p.add_run(text)
    r.font.color.rgb = TEAL
    r.font.bold = True


def h3(doc, text):
    p = doc.add_heading(text, 3)
    r = p.runs[0] if p.runs else p.add_run(text)
    r.font.color.rgb = ORANGE
    r.font.bold = True


def para(doc, text, bold=False, color=None, size=11, indent=0):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    if color:
        r.font.color.rgb = color
    return p


def bullet(doc, text, level=0, color=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(level * 0.7 + 0.4)
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    if color:
        r.font.color.rgb = color


def note_box(doc, label, text, label_color=TEAL):
    """Renders a coloured callout box."""
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    c = t.rows[0].cells[0]
    _cell_bg(c, "EBF5FB")
    c.paragraphs[0].clear()
    lp = c.add_paragraph()
    lr = lp.add_run(label + "  ")
    lr.font.bold = True
    lr.font.color.rgb = label_color
    lr.font.size = Pt(10)
    tr = lp.add_run(text)
    tr.font.size = Pt(10)
    first = c.paragraphs[0]
    if not first.text:
        first._element.getparent().remove(first._element)
    doc.add_paragraph()


def warning_box(doc, text):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    c = t.rows[0].cells[0]
    _cell_bg(c, "FDF2E9")
    c.paragraphs[0].clear()
    p = c.add_paragraph()
    r = p.add_run("⚠  Without this:  ")
    r.font.bold = True
    r.font.color.rgb = RED
    r.font.size = Pt(10)
    rb = p.add_run(text)
    rb.font.size = Pt(10)
    first = c.paragraphs[0]
    if not first.text:
        first._element.getparent().remove(first._element)
    doc.add_paragraph()


def code(doc, lines):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    c = t.rows[0].cells[0]
    _cell_bg(c, "1E1E1E")
    c.paragraphs[0].clear()
    for line in lines:
        p = c.add_paragraph()
        r = p.add_run(line)
        r.font.name = "Courier New"
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0xD4, 0xD4, 0xD4)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
    first = c.paragraphs[0]
    if not first.text:
        first._element.getparent().remove(first._element)
    doc.add_paragraph()


def table(doc, headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        _cell_bg(c, "002D62")
        r = c.paragraphs[0].add_run(h)
        r.font.bold = True
        r.font.color.rgb = WHITE
        r.font.size = Pt(9.5)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for ri, row in enumerate(rows):
        bg = "F2F2F2" if ri % 2 == 0 else "FFFFFF"
        for ci, val in enumerate(row):
            c = t.rows[ri + 1].cells[ci]
            _cell_bg(c, bg)
            r = c.paragraphs[0].add_run(val)
            r.font.size = Pt(9.5)
    doc.add_paragraph()


def divider(doc):
    p = doc.add_paragraph()
    pr = p._p.get_or_add_pPr()
    pb = OxmlElement("w:pBdr")
    b  = OxmlElement("w:bottom")
    b.set(qn("w:val"),   "single")
    b.set(qn("w:sz"),    "4")
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), "007A87")
    pb.append(b)
    pr.append(pb)


def qa_block(doc, question, answer):
    """Renders a Q&A block with visual distinction."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    qr = p.add_run("Q:  " + question)
    qr.font.bold = True
    qr.font.color.rgb = NAVY
    qr.font.size = Pt(11)

    p2 = doc.add_paragraph()
    p2.paragraph_format.left_indent = Cm(0.6)
    ar = p2.add_run("A:  " + answer)
    ar.font.size = Pt(10.5)
    ar.font.color.rgb = GREY
    doc.add_paragraph()


# ─────────────────────────────────────────────────────────────────────────────
# Document sections
# ─────────────────────────────────────────────────────────────────────────────

def cover(doc):
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("BugBuddy")
    r.font.size  = Pt(38)
    r.font.bold  = True
    r.font.color.rgb = NAVY

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("AI-Powered Test Gap Analyzer")
    r2.font.size = Pt(18)
    r2.font.color.rgb = TEAL

    doc.add_paragraph()
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run("End-to-End Architecture  ·  Technical Deep-Dive Reference")
    r3.font.size   = Pt(12)
    r3.font.italic = True
    r3.font.color.rgb = GREY
    doc.add_paragraph()
    divider(doc)


def section_overview(doc):
    h1(doc, "1. What Is BugBuddy?  (30-second pitch)")
    para(doc, (
        "BugBuddy is a production AI application that reads a Jira bug report — including "
        "every comment, attachment, log file, and screenshot description — and automatically "
        "generates a set of test cases that, had they existed before the bug was filed, would "
        "have caught the defect before it reached customers."
    ))
    doc.add_paragraph()
    para(doc, (
        "It does this by building a multi-step AI pipeline: "
        "it scrubs raw Jira data into clean text, enriches the prompt with organisation-specific "
        "knowledge via RAG, sends the text to a large language model (LLM), validates the output "
        "against a strict schema, scores the quality using a second LLM call, caches everything "
        "in Redis to avoid repeating expensive calls, and stores each analysis as a vector "
        "embedding in ChromaDB so that similar bugs can be found in the future."
    ))
    doc.add_paragraph()
    note_box(doc, "Key value:", (
        "A QA engineer who would normally spend 2 hours reading a bug report and writing test "
        "cases gets the same result in under 60 seconds, and every run makes the next run smarter "
        "because similar past analyses are retrieved and used as examples."
    ))


def section_full_flow(doc):
    h1(doc, "2. The Complete Request Flow — Step by Step")
    para(doc, (
        "Every time a user selects a Jira issue and clicks Analyse, the following steps happen "
        "in sequence. Each step is handled by a dedicated Python module. Understanding why each "
        "step exists is more important than remembering the code."
    ))
    doc.add_paragraph()

    # ── STEP 1 ──
    h2(doc, "Step 1  →  User Submits Filter  (jira_filter.py)")
    para(doc, (
        "The user fills in a web form: project = CFSHELF, fix version = 9.14, issue type = Bug. "
        "The FilterParams dataclass captures these values and the JiraQueryEngine translates them "
        "into a JQL (Jira Query Language) string — Jira's own SQL-like query syntax — and fires "
        "a paginated REST API call to the Jira server, fetching up to 200 issues in batches of 50."
    ))
    bullet(doc, "JQL built:  project = CFSHELF AND issuetype = Bug AND fixVersion = \"9.14\" ORDER BY created DESC")
    bullet(doc, "Batch size 50 is safe per Jira's API guidance — larger batches can time out on big projects")
    bullet(doc, "Custom fields like \"Target Release\" are auto-discovered by scanning all Jira field names at startup")
    warning_box(doc, (
        "Without JQL translation, the user would have to manually write JQL strings, "
        "which most QA engineers don't know. The FilterParams → JQL layer is the UX abstraction layer."
    ))

    # ── STEP 2 ──
    h2(doc, "Step 2  →  Jira Issue Scrubbing  (jira_scrubber.py)")
    para(doc, (
        "For each issue the API returns only metadata. jira_scrubber.py makes a second API call "
        "to fetch the full issue body: summary, description, all comments, and all attachments. "
        "It then extracts readable text from every attachment regardless of format."
    ))
    para(doc, "Why do we scrub?  Because raw Jira content is extremely noisy:", bold=True)
    bullet(doc, "Descriptions contain Jira markup: {color:red}text{color}, *bold*, [link|url], h3. headings")
    bullet(doc, "Attachments are binary files: PDFs, Word docs, ZIP archives containing log files")
    bullet(doc, "Log files inside ZIPs are the most valuable content — they show the exact failure trace")
    doc.add_paragraph()

    table(doc,
        ["Attachment Type", "How Text Is Extracted", "Why This Format Appears in Jira"],
        [
            ["PDF",         "pdfminer — reads text layer",            "Test reports, crash dumps"],
            ["DOCX",        "python-docx — reads paragraphs",         "Architecture docs attached to bugs"],
            ["XLSX",        "openpyxl — reads cells sheet-by-sheet",  "Test matrices, config tables"],
            ["ZIP",         "zipfile — extracts members as text",      "Log bundles, firmware traces"],
            ["TAR/BZ2",     "tarfile — extracts members as text",      "Linux log archives"],
            ["RTF",         "striprtf — converts to plain text",       "Older tools generate RTF reports"],
            ["gzip",        "gzip.decompress then re-detect format",   "Compressed kernel logs"],
            ["Plain text",  "UTF-8 decode with error replacement",     "Most common — .log, .txt, .conf"],
        ]
    )
    para(doc, (
        "After scrubbing, the entire issue — description + all comments + all attachment text — "
        "is concatenated into a single string called full_text. This is the canonical "
        "representation of the bug that everything else in the pipeline operates on."
    ))
    warning_box(doc, (
        "Without scrubbing, the LLM receives Jira markup noise like {color:red} and unreadable "
        "binary attachment references. The model wastes tokens on formatting artefacts and "
        "misses the actual log content inside ZIP files, which is usually the most important signal."
    ))

    # ── STEP 3 ──
    h2(doc, "Step 3  →  Redis Cache Check  (cache.py)")
    para(doc, (
        "Before doing any expensive work, BugBuddy checks Redis: "
        "has this exact issue already been analysed with this exact provider and model? "
        "If yes, return the cached result immediately. The user gets their answer in under 100ms "
        "instead of waiting 60 seconds."
    ))
    para(doc, "Three separate cache tiers with different TTLs (Time-To-Live):", bold=True)
    table(doc,
        ["Cache Tier", "Redis Key Pattern", "TTL", "What Is Stored"],
        [
            ["Jira Scrape",  "bb:scrape:<ISSUE-KEY>",               "10 min", "The full scraped text dict (JSON + gzip)"],
            ["RAG Glossary", "bb:rag:<SHA256 of first 4000 chars>",  "1 hour", "Org terminology explanation returned by knowledge proxy"],
            ["LLM Result",   "bb:llm:<provider>:<model>:<key>:<SHA256 of full_text>",
             "24 hours", "The final list of test case JSON objects"],
        ]
    )
    para(doc, "How cache keys are built:", bold=True)
    bullet(doc, "Jira scrape key: just the issue key string (e.g. bb:scrape:CFSHELF-4291)")
    bullet(doc, "RAG key: SHA-256 hash of the first 4000 characters of full_text — same excerpt always maps to same glossary")
    bullet(doc, "LLM key: SHA-256 hash of the ENTIRE full_text, combined with provider+model+issue_key — changing any one of these is a cache miss")
    bullet(doc, "All values are JSON-serialised then gzip-compressed before storage — a 50KB full_text blob becomes ~8KB in Redis")
    doc.add_paragraph()
    note_box(doc, "Content-addressed caching:", (
        "Using SHA-256 hashes of the content (not timestamps) means the cache is "
        "automatically invalidated when the issue changes — because the hash of the new "
        "full_text will be different. This is called content-addressed caching, the same "
        "pattern used by Git."
    ))
    warning_box(doc, (
        "Without Redis cache, every single analysis — even the same issue opened by "
        "two different team members 5 minutes apart — makes a fresh Jira API call, "
        "a fresh RAG proxy call, and a fresh LLM call. At scale with 50 engineers "
        "analysing bugs daily that is 150+ LLM calls per day that could be served from cache. "
        "At $0.10 per analysis that is $15/day wasted, plus 50x worse latency."
    ))

    # ── STEP 4 ──
    h2(doc, "Step 4  →  RAG — Retrieval-Augmented Generation  (org_rag.py)")
    para(doc, (
        "RAG is the technique of injecting retrieved external knowledge into the LLM prompt "
        "before asking the model to answer. Without RAG, a general-purpose LLM like GPT-4o "
        "has no idea what 'PERST#', 'WAFL', 'SFO', or 'CFSHELF' mean — these are NetApp-internal "
        "terms that never appear in the model's training data."
    ))
    doc.add_paragraph()
    para(doc, "How the RAG step works in BugBuddy:", bold=True)
    bullet(doc, "Take only the first 4,000 characters of full_text (enough to identify all technical terms, but cheap to process)")
    bullet(doc, "Send this excerpt to an internal NetApp knowledge proxy — a domain-tuned model that has been trained on NetApp internal docs")
    bullet(doc, "The proxy returns a bullet-list glossary: '• PERST#: PCI Express Reset, active-low signal...'")
    bullet(doc, "This glossary is injected into the LLM system prompt as a third knowledge layer")
    doc.add_paragraph()
    para(doc, "Why only 4,000 characters for RAG?", bold=True)
    para(doc, (
        "Because the RAG step's only job is term identification — we don't need the full 600K-char "
        "log to find the terms 'PERST#' and 'NSSR'. The first 4K chars of a bug report always "
        "contain the summary, description, and first comment — which mention every relevant term. "
        "Sending the full text would cost 150x more in tokens for zero extra benefit."
    ))
    warning_box(doc, (
        "Without RAG, when the LLM sees 'PERST# deasserted and CSTS.RDY never set', it might "
        "guess 'PERST# is some kind of permission flag' rather than understanding it is the "
        "PCIe hardware reset pin. The generated test cases would be generic and miss the actual "
        "hardware interaction that caused the bug."
    ))

    # ── STEP 5 ──
    h2(doc, "Step 5  →  Few-Shot Retrieval from Vector Store  (embeddings.py)")
    para(doc, (
        "Few-shot prompting means giving the LLM 2-3 examples of the format you want before "
        "asking it to generate new content. The quality of LLM output improves dramatically "
        "when it can see what 'good' looks like."
    ))
    para(doc, (
        "BugBuddy retrieves examples dynamically from ChromaDB — a vector database — "
        "by finding past analyses of bugs that are semantically similar to the current one. "
        "If CFSHELF-4291 is about an NVMe drive disappearing after a reset, and there is a past "
        "analysis of CFSHELF-3872 (another reset-related bug), the test cases from 3872 are "
        "injected into the prompt as examples."
    ))
    doc.add_paragraph()
    h3(doc, "What Is Embedded?")
    para(doc, (
        "Embedding is the process of converting text into a fixed-length list of numbers "
        "(a vector) that captures the meaning of the text. Similar texts produce vectors "
        "that are close together in high-dimensional space."
    ))
    para(doc, "Specifically, BugBuddy embeds:", bold=True)
    bullet(doc, "issue_key + first 8,000 characters of full_text (summary + description + early comments)")
    bullet(doc, "This is called the embed_text — it captures what the bug is about, not the full log noise")
    bullet(doc, "The resulting vector is 384 dimensions (sentence-transformers) or 1,536 dimensions (OpenAI)")
    doc.add_paragraph()
    h3(doc, "Embedding Model Used")
    table(doc,
        ["EMBED_PROVIDER setting", "Model", "Dimensions", "Requires API Key?", "Best For"],
        [
            ["sentence (default)", "all-MiniLM-L6-v2\n(sentence-transformers)",
             "384", "No — runs locally", "Air-gapped / on-prem environments"],
            ["openai",             "text-embedding-3-small",
             "1,536", "Yes — OPENAI_API_KEY", "Higher accuracy, cloud environments"],
            ["mock",               "MD5-derived unit vectors",
             "16",   "No",                   "Unit tests, CI only"],
        ]
    )
    h3(doc, "How ChromaDB Stores the Vectors")
    para(doc, (
        "ChromaDB is an embedded vector database — it runs inside the same Python process, "
        "no separate server needed. It uses an HNSW (Hierarchical Navigable Small World) index "
        "for approximate nearest-neighbour search, which makes similarity lookups fast even with "
        "millions of vectors."
    ))
    bullet(doc, "Each issue is stored with: its issue_key as the ID, the 384/1536-dim embedding vector, and metadata (issue_key, tc_count)")
    bullet(doc, "Test cases (the actual JSON output) are stored as a sidecar .json file in chroma_store/testcases/CFSHELF-4291.json")
    bullet(doc, "ChromaDB uses cosine distance (1 - cosine_similarity) for retrieval — so similarity 0.92 means the vectors are 92% aligned")
    bullet(doc, "The collection is named bugbuddy_analyses and persists to disk in the CHROMA_PERSIST_DIR folder")
    doc.add_paragraph()
    note_box(doc, "Why not PostgreSQL/MongoDB for vector storage?", (
        "PostgreSQL and MongoDB are row/document stores optimised for exact lookups and range queries. "
        "Finding 'the 3 most similar bugs' requires computing cosine similarity between your query vector "
        "and every stored vector — a relational DB does this in O(n) full scans. "
        "ChromaDB's HNSW index does it in O(log n). For 100K stored analyses, PostgreSQL would take "
        "seconds per query; ChromaDB takes milliseconds. "
        "(Note: pgvector is a PostgreSQL extension that adds vector search — it could be a valid "
        "production choice if the team already runs PostgreSQL.)"
    ))
    warning_box(doc, (
        "Without few-shot retrieval, the LLM generates test cases based only on the current bug "
        "and the system prompt. With it, the model can see 'for a similar bug, a QA engineer "
        "previously wrote these test cases' — it learns the house style, the level of detail "
        "expected, and avoids repeating gaps already covered for similar bugs."
    ))

    # ── STEP 6 ──
    h2(doc, "Step 6  →  Context Builder — Assembling the LLM Prompt  (llm_agent.py)")
    para(doc, (
        "Before calling the LLM, BugBuddy assembles the complete prompt from three layers. "
        "Think of this as building a dossier that gives the LLM everything it needs to do "
        "its job correctly."
    ))
    code(doc, [
        "  SYSTEM PROMPT = [",
        "    Layer 1: Base instructions (role, task, output JSON schema)",
        "    Layer 2: Static org glossary from org_context.yaml",
        "             → PERST#, WAFL, NVRAM, SFO, RDB, LIF, ACP, AGGR...",
        "    Layer 3: Dynamic RAG glossary from org_rag.py",
        "             → '• PERST#: PCI Express Reset, active-low...'",
        "  ]",
        "",
        "  USER PROMPT = [",
        "    Few-shot examples from ChromaDB (similar past analyses)",
        "    Full Jira issue text (this specific bug's full_text)",
        "  ]",
    ])
    para(doc, "Chain-of-Thought (CoT) instruction:", bold=True)
    para(doc, (
        "The system prompt includes the instruction 'Think step by step: 1) identify the root cause, "
        "2) identify what scenario triggers it, 3) write the test case.' "
        "This CoT prompt forces the LLM to reason before writing, which is proven to reduce "
        "hallucinations and improve the quality of structured outputs."
    ))
    para(doc, "Output schema enforced in the prompt:", bold=True)
    bullet(doc, "tc_number (string, e.g. TC-001), title, gap_reason, preconditions, steps (list), expected, test_type")
    bullet(doc, "temperature=0.2 — makes the output near-deterministic so caching is safe and results are comparable")
    bullet(doc, "'Return ONLY valid JSON' instruction prevents the LLM from wrapping the response in prose")

    # ── STEP 7 ──
    h2(doc, "Step 7  →  Handling Huge Data: Chunking  (llm_agent.py)")
    para(doc, (
        "LLMs have a context window limit — the maximum amount of text they can read in one call. "
        "GPT-4o supports ~128K tokens (roughly 512KB of text). A large Jira issue with 50 comments "
        "and a 2MB log archive can easily exceed this."
    ))
    para(doc, "BugBuddy's chunking strategy:", bold=True)
    bullet(doc, "Chunk size: 600,000 characters ≈ 150,000 tokens. This fits comfortably in GPT-4o (128K) and Claude (200K) with room for the system prompt and response")
    bullet(doc, "Overlap: 3,000 characters of the previous chunk are repeated at the start of the next chunk")
    bullet(doc, "Why overlap? A critical error trace might span the boundary between chunk 1 and chunk 2. Repeating 3K chars ensures the LLM sees the full context around the boundary")
    bullet(doc, "Each chunk is sent as an independent LLM call: 'This is PART 2 of 4 of issue CFSHELF-4291...'")
    bullet(doc, "Results from all chunks are merged and deduplicated using Jaccard similarity on test case titles (70% word overlap = duplicate)")
    doc.add_paragraph()
    code(doc, [
        "  Example: full_text = 1,800,000 chars → 3 chunks",
        "",
        "  Chunk 1: chars 0      → 600,000",
        "  Chunk 2: chars 597,000 → 1,197,000  (3K overlap with chunk 1)",
        "  Chunk 3: chars 1,194,000 → 1,800,000 (3K overlap with chunk 2)",
        "",
        "  3 parallel LLM calls (ThreadPoolExecutor, max 4 workers)",
        "  → 3 lists of test cases",
        "  → merged + deduplicated",
        "  → renumbered TC-001, TC-002 ...",
    ])
    warning_box(doc, (
        "Without chunking, any issue larger than ~512KB would either be silently truncated "
        "(losing the most recent comments and the most detailed log attachments, which are "
        "usually at the end) or would crash with a 'context length exceeded' API error."
    ))

    # ── STEP 8 ──
    h2(doc, "Step 8  →  Guardrails  (guardrails.py)")
    para(doc, (
        "Before the full_text is sent to an external LLM (OpenAI, Anthropic, Gemini), "
        "it passes through the guardrails module. This runs two checks:"
    ))
    bullet(doc, "PII Redaction: email addresses, IPv4 addresses, phone numbers, and credit card patterns are replaced with [REDACTED-EMAIL], [REDACTED-IP] etc. Internal providers (NetApp proxy) skip this because data never leaves the corporate network")
    bullet(doc, "Prompt Injection Detection: scans for phrases like 'ignore all previous instructions' or '<|system|>' tokens that malicious content in a Jira comment might use to hijack the LLM")
    warning_box(doc, (
        "Without PII redaction, a Jira comment like 'engineer john@netapp.com reproduces this at "
        "10.1.2.3' would send real employee email addresses and internal IP addresses to a "
        "third-party API. This is a GDPR / data-handling violation in most enterprise environments."
    ))

    # ── STEP 9 ──
    h2(doc, "Step 9  →  Provider Fallback  (llm_agent.py)")
    para(doc, (
        "LLM APIs fail. OpenAI rate-limits, Anthropic has outages, internal proxies go down "
        "for maintenance. BugBuddy's fallback chain automatically tries the next configured "
        "provider if the primary one fails, so analyses complete even during partial outages."
    ))
    code(doc, [
        "  LLM_FALLBACK_CHAIN = 'openai,anthropic,gemini'",
        "",
        "  Attempt 1: Call OpenAI GPT-4o  → 429 Rate Limit error",
        "  Attempt 2: Call Anthropic Claude → Success",
        "  → Return result, log which provider was actually used",
    ])

    # ── STEP 10 ──
    h2(doc, "Step 10  →  LLM Call and Response Processing  (llm_agent.py)")
    para(doc, (
        "The LLM returns a raw string — hopefully a JSON array, but in practice it might come "
        "back wrapped in markdown code fences (```json ... ```), or as a single object instead "
        "of a list, or with one malformed item in a list of ten valid ones."
    ))
    para(doc, "Processing the raw LLM response (parse_llm_output in models.py):", bold=True)
    bullet(doc, "Strip ```json ... ``` markdown fences if present")
    bullet(doc, "json.loads() the string — if this fails, do a regex fallback to find the first [ ... ] block")
    bullet(doc, "Pass each item through Pydantic's TestCase model for schema validation")
    bullet(doc, "Items that fail validation (wrong type, missing field, invalid test_type enum) are skipped with a warning log — they do not crash the run")
    bullet(doc, "Valid items are returned as a typed list of TestCase objects")
    doc.add_paragraph()
    note_box(doc, "Why Pydantic?", (
        "Pydantic enforces the JSON schema at the Python type level. "
        "A test_type field that says 'Funtional' (typo) gets rejected. "
        "A tc_number that says 'TC-1' gets normalised to 'TC-001'. "
        "A steps field that is a single string instead of a list gets coerced to a one-item list. "
        "This means downstream code (Excel export, UI rendering) can always trust the data shape."
    ))

    # ── STEP 11 ──
    h2(doc, "Step 11  →  LLM-as-Judge Quality Scoring  (evaluator.py)")
    para(doc, (
        "After the primary LLM generates test cases, a second, cheaper LLM call acts as an "
        "independent judge. This pattern is called LLM-as-Judge or self-critique. "
        "The judge is deliberately a different model (gpt-4o-mini instead of gpt-4o) to "
        "reduce self-confirmation bias — you don't want the generator marking its own homework."
    ))
    para(doc, "The judge scores each test case on four dimensions (1–5):", bold=True)
    bullet(doc, "Specificity — are the steps concrete and executable, or vague?")
    bullet(doc, "Coverage — does the test actually address the stated gap reason?")
    bullet(doc, "Completeness — are preconditions, steps, and expected result all present?")
    bullet(doc, "Actionability — could a QA engineer run this without asking follow-up questions?")
    bullet(doc, "Composite score = mean of all four. Grade: Excellent (≥4.5), Good (≥3.5), Adequate (≥2.5), Poor (<2.5)")
    doc.add_paragraph()
    note_box(doc, "temperature=0.0 for the judge:", (
        "The primary LLM uses temperature=0.2 for slightly varied but deterministic output. "
        "The judge uses temperature=0.0 (fully deterministic) because we want consistent "
        "scoring — the same test case should always get the same score."
    ))

    # ── STEP 12 ──
    h2(doc, "Step 12  →  Store in Vector DB and Cache Result  (embeddings.py, cache.py)")
    para(doc, (
        "After the analysis is complete, two storage operations run in parallel:"
    ))
    bullet(doc, "ChromaDB: embed the issue text and store the vector + test case sidecar JSON. This feeds future few-shot retrieval")
    bullet(doc, "Redis: store the test case list under the LLM cache key (bb:llm:...) with a 24-hour TTL")
    doc.add_paragraph()

    # ── STEP 13 ──
    h2(doc, "Step 13  →  Observability Trace  (observability.py)")
    para(doc, (
        "Every LLM call emits a structured JSON log line containing: trace_id, provider, model, "
        "issue_key, latency_ms, prompt_tokens, completion_tokens, estimated_cost_usd, "
        "cache_hit, rag_used, pii_redactions, quality_score."
    ))
    para(doc, (
        "These log lines can be shipped to any log aggregator (CloudWatch, Datadog, Grafana Loki). "
        "The /api/stats endpoint aggregates the in-memory rolling window of the last 500 calls "
        "into a dashboard: cache hit rate, p95 latency, total cost, average quality score."
    ))


def section_data_flow_diagram(doc):
    h1(doc, "3. Architecture Diagram — Full Data Flow")
    doc.add_paragraph()
    code(doc, [
        "  Browser  ──(1) FilterParams──►  Flask API (app.py)",
        "                                       │",
        "                              (2) JQL query",
        "                                       │",
        "                                       ▼",
        "                               Jira Server (REST)",
        "                                       │",
        "                              (3) Raw issues + attachments",
        "                                       │",
        "                                       ▼",
        "                               JiraScrubber (jira_scrubber.py)",
        "                               ─ strips Jira markup",
        "                               ─ extracts text from PDF/DOCX/ZIP/TAR",
        "                               ─ produces: full_text blob",
        "                                       │",
        "               ┌───────────────────────┤",
        "               │                       │",
        "         (4a) Cache check          (4b) Cache check",
        "          Redis bb:scrape:KEY       Redis bb:llm:HASH",
        "               │ MISS                  │ MISS",
        "               │                       │",
        "               ▼                       ▼",
        "          (5) RAG Step            (6) Few-Shot Retrieval",
        "           org_rag.py              embeddings.py",
        "           first 4K chars ──►     query vector ──►",
        "           NetApp proxy            ChromaDB HNSW index",
        "           returns glossary        returns top-3 similar",
        "               │                  analyses + their TCs",
        "               └───────────┬───────────┘",
        "                           │",
        "                           ▼",
        "                   (7) Prompt Assembly",
        "                    System: Base + YAML glossary + RAG glossary",
        "                    User:   Few-shot examples + full_text chunks",
        "                           │",
        "                  (8) Guardrails (guardrails.py)",
        "                    ─ PII redaction",
        "                    ─ Prompt injection check",
        "                           │",
        "                           ▼",
        "                    (9) LLM Router (llm_agent.py)",
        "                         │      │      │      │",
        "                      GPT-4o  Claude  Gemini  NetApp",
        "                     (or fallback chain if primary fails)",
        "                           │",
        "                           ▼",
        "              (10) parse_llm_output (models.py)",
        "                    ─ strip markdown fences",
        "                    ─ Pydantic validation",
        "                    ─ normalise TC numbers",
        "                           │",
        "               (multi-chunk: merge + dedup)",
        "                           │",
        "              (11) LLM-as-Judge (evaluator.py)",
        "                    ─ gpt-4o-mini scores each TC",
        "                    ─ adds quality_score, quality_grade",
        "                           │",
        "               ┌───────────┴───────────┐",
        "               ▼                       ▼",
        "        (12a) Store vector         (12b) Store LLM result",
        "          ChromaDB                  Redis bb:llm:HASH TTL=24h",
        "          + sidecar JSON",
        "               │                       │",
        "               └───────────┬───────────┘",
        "                           ▼",
        "              (13) Observability trace",
        "                    tracer.emit() → JSON log line",
        "                           │",
        "                           ▼",
        "               Browser ◄── JSON test cases",
        "                           + Excel export",
        "                           + SSE streaming updates",
    ])


def section_interviewer_qa(doc):
    h1(doc, "4. Technical Q&A — Design Decisions and Implementation Details")

    para(doc, (
        "These are the types of questions a technical reviewer or architect may raise to understand "
        "the reasoning behind each design decision. Each answer is a direct, precise response that "
        "demonstrates implementation depth and the trade-offs considered."
    ))
    divider(doc)
    doc.add_paragraph()

    qa_block(doc,
        "After scrubbing huge chunks of data from Jira, how do you store it in a NoSQL database?",
        (
            "We use two different stores for two different purposes. "
            "The scraped full_text is not stored long-term as a document — it is a transient "
            "intermediate. However, we persist two derived representations: "
            "(1) A gzip-compressed JSON blob in Redis under the key bb:scrape:<ISSUE-KEY> with a "
            "10-minute TTL — this acts as a short-lived document cache so the Jira API is not "
            "hammered on repeated requests. "
            "(2) A 384-dimensional embedding vector in ChromaDB along with a JSON sidecar file "
            "containing the generated test cases. ChromaDB is a vector database with an HNSW "
            "index — it is the right tool for semantic similarity lookup, which is what we need "
            "for few-shot retrieval. If the question is specifically about PostgreSQL, the "
            "pgvector extension adds vector column support to Postgres and would be a valid "
            "alternative in an environment that already runs PostgreSQL."
        )
    )

    qa_block(doc,
        "What embedding model do you use, and which data exactly gets embedded?",
        (
            "By default we use sentence-transformers/all-MiniLM-L6-v2, which runs locally — "
            "no API key, no data leaving the network. It produces 384-dimensional vectors. "
            "For cloud deployments we switch to OpenAI's text-embedding-3-small which gives "
            "1,536 dimensions at a small per-token cost. "
            "What gets embedded: we embed the string issue_key + first 8,000 characters of "
            "full_text. We use 8K chars because embedding models have their own token limits "
            "(typically 512 tokens for MiniLM, 8K for OpenAI). The first 8K of a Jira issue "
            "always contains the summary and description — the most semantically meaningful "
            "content. The 600KB of log files appended later contains repeated stack traces that "
            "would not improve the embedding quality and would be truncated anyway."
        )
    )

    qa_block(doc,
        "How do you send such a huge amount of data to the LLM if it has a context window limit?",
        (
            "We use a sliding-window chunking strategy. The full_text is split into chunks of "
            "600,000 characters each — roughly 150,000 tokens — which fits comfortably within "
            "GPT-4o's 128K token window after accounting for the system prompt (~2K tokens) and "
            "the expected JSON response (~4K tokens). "
            "Each chunk gets a 3,000-character overlap with the previous chunk. The overlap is "
            "critical: a crash stack trace might be split across the boundary between chunk 1 "
            "and chunk 2, and without the overlap, neither chunk would see the complete trace. "
            "Multiple chunks are dispatched concurrently using a Python ThreadPoolExecutor "
            "(max 4 workers) because LLM calls are I/O-bound — we are waiting on the HTTP "
            "response, not doing CPU work. The test cases from all chunks are then merged and "
            "deduplicated using Jaccard similarity on the test case titles: if two titles share "
            "70% of their words, they are considered the same test case and only one is kept."
        )
    )

    qa_block(doc,
        "Why use Redis cache? Can we not just call the LLM every time?",
        (
            "You can, but it is expensive, slow, and unnecessary. "
            "Consider: a typical Jira issue analysis takes 30–60 seconds and costs $0.05–$0.20 "
            "in API tokens. In a team of 20 QA engineers, the same popular bug (like a release "
            "blocker) might be opened and analysed 10 times in a day. Without cache that is "
            "$2 and 10 minutes of waiting for zero new information — the answer is identical "
            "every time because the input has not changed. "
            "Cache also absorbs load spikes: if 5 engineers hit Analyse at the same moment, "
            "only the first request hits the LLM; the other 4 get the cached response "
            "instantly. "
            "We use three TTL tiers because different data has different staleness tolerances: "
            "Jira content changes frequently (10-min TTL), the org terminology glossary barely "
            "changes (1-hour TTL), and LLM results are deterministic at temperature=0.2 so they "
            "can be held for 24 hours. The application works fine without Redis — every cache "
            "call degrades silently to a miss — but teams pay 10–50x more in API costs."
        )
    )

    qa_block(doc,
        "Why do you use two separate LLM calls — generator and judge?",
        (
            "A single LLM generating and reviewing its own output has a strong self-confirmation "
            "bias. It will rarely call its own output vague or incomplete. "
            "By using a second, different model call at temperature=0.0 (fully deterministic), "
            "we get an independent evaluation against four concrete rubric dimensions. "
            "The judge also provides a composite quality score (1–5) and a one-sentence "
            "note on the main weakness, which the QA team uses to prioritise which test cases "
            "to actually implement first. Test cases scoring below 2.5 (grade: Poor) are flagged "
            "in the Excel export in red so they are not blindly used."
        )
    )

    qa_block(doc,
        "What is RAG and why do you need it here?",
        (
            "RAG stands for Retrieval-Augmented Generation. The concept is simple: before asking "
            "the LLM to generate output, you first retrieve relevant knowledge and inject it into "
            "the prompt. The LLM does not need to have been trained on that knowledge — it just "
            "reads it in context. "
            "We need RAG because GPT-4o was never trained on NetApp internal documentation. "
            "When the LLM sees 'NSSR caused CSTS.RDY to never be set after PERST# deasserted', "
            "without RAG it has no idea what NSSR (NVM Subsystem Reset) or PERST# (PCIe hardware "
            "reset pin) or CSTS.RDY (NVMe controller ready bit) mean. With RAG, the prompt "
            "includes a glossary explaining exactly what each term means in NetApp's context, "
            "so the generated test cases correctly target the hardware reset sequence instead of "
            "generating vague 'verify the device resets correctly' steps."
        )
    )

    qa_block(doc,
        "How do you prevent bad or malicious input from being sent to the LLM?",
        (
            "The guardrails module runs two checks before any text leaves the system. "
            "First, PII redaction: we use compiled regular expressions to find and replace "
            "email addresses, IPv4 addresses, phone numbers, and credit card patterns with "
            "typed placeholders like [REDACTED-EMAIL]. This is enforced only for external "
            "providers — the internal NetApp proxy never leaves the corporate network so "
            "redaction is skipped. "
            "Second, prompt injection detection: we scan the input for patterns like "
            "'ignore all previous instructions', '<|system|>' tokens, and '[INST]' markers "
            "that could hijack the LLM's behaviour. If detected, the request is blocked "
            "and an error is returned before any API call is made. "
            "We acknowledge the limitation: a determined attacker could base64-encode a "
            "payload or use Unicode lookalike characters — there is a FIXME comment in the "
            "code noting this gap for a future iteration."
        )
    )

    qa_block(doc,
        "How does the streaming SSE endpoint work?",
        (
            "SSE stands for Server-Sent Events — a standard HTTP mechanism where the server "
            "pushes a stream of events to the browser over a single long-lived HTTP connection. "
            "The /api/stream-analyse endpoint runs the same pipeline as the regular analyse "
            "endpoint, but instead of waiting for everything to finish before responding, "
            "it yields a data: {JSON} line at each stage: stage=scrape, stage=rag, stage=llm, "
            "stage=evaluate, stage=done. "
            "The browser's EventSource API listens to this stream and updates a progress bar "
            "in real time. For a 3-chunk issue that takes 45 seconds, the user sees 'Scraping "
            "Jira...' → 'RAG lookup...' → 'Calling GPT-4o chunk 1/3...' instead of a frozen "
            "spinner for 45 seconds."
        )
    )

    qa_block(doc,
        "How does the feedback loop work and why does it matter?",
        (
            "After the UI displays the generated test cases, each one has a 1-5 star rating "
            "widget. When the user rates a test case, the /api/feedback endpoint receives the "
            "rating and stores it back into ChromaDB as metadata on the corresponding issue's "
            "record (using ChromaDB's collection.update() call). "
            "Why does this matter? Currently it surfaces in the /api/stats endpoint so teams "
            "can see 'average quality score for gpt-4o = 4.1, for gemini-flash = 3.2' and "
            "choose their provider accordingly. "
            "In a future iteration, the few-shot retrieval step could weight similar past "
            "analyses by their average user rating — so highly-rated past analyses are "
            "prioritised as examples. This is a lightweight version of RLHF "
            "(Reinforcement Learning from Human Feedback) applied at retrieval time."
        )
    )

    qa_block(doc,
        "Why is JSON used for prompt engineering and output post-processing? Could we manage without it?",
        (
            "Short answer: technically yes, but it would make the application fragile and "
            "unreliable in practice. Here is the problem JSON solves and what happens without it.\n\n"
            "The core challenge is that an LLM returns free-form text. If you ask it to generate "
            "test cases with no format constraint, it might reply in any of these ways:\n\n"
            "  Without JSON — what the LLM might return:\n"
            "  'Here are 3 test cases for CFSHELF-4291:\n"
            "   Test Case 1: Verify NVMe drive reconnects after PERST#.\n"
            "   Steps: 1. Power on system. 2. Trigger PERST#. 3. Check dmesg.'\n\n"
            "This is readable to a human but completely unusable for the application. "
            "The Flask API cannot pass free text to the Excel exporter, the UI renderer, "
            "the Pydantic validator, ChromaDB storage, the LLM-as-Judge scorer, or the "
            "Redis cache — all of which expect structured data with known fields.\n\n"
            "  With JSON — what the LLM returns (instructed in the prompt):\n"
            "  [{\n"
            "    \"tc_number\": \"TC-001\",\n"
            "    \"title\": \"Verify NVMe drive reconnects after PERST# deassert\",\n"
            "    \"test_type\": \"Functional\",\n"
            "    \"preconditions\": [\"System powered on\", \"NVMe drive present\"],\n"
            "    \"steps\": [\"Trigger PERST# signal\", \"Wait 500ms\", \"Check dmesg for re-enumeration\"],\n"
            "    \"expected\": \"Drive reappears in /dev within 2 seconds\",\n"
            "    \"gap_reason\": \"No existing test covers post-reset re-enumeration timing\"\n"
            "  }]\n\n"
            "Now every downstream component gets reliable, predictable data. The prompt explicitly "
            "tells the LLM: 'Return ONLY a valid JSON array. No prose. No markdown fences.' "
            "This is called structured output prompting — JSON acts as a contract between the "
            "LLM and the rest of the system.\n\n"
            "Even with this instruction, LLMs sometimes still wrap the output in ```json ... ``` "
            "markdown fences, or return a single object instead of a list. This is why the "
            "parse_llm_output() function in models.py exists: it strips fences, normalises "
            "single-object responses into a list, then passes every item through Pydantic for "
            "field-level validation. Items that fail are dropped individually — the run does not "
            "crash just because one of ten test cases has a malformed field.\n\n"
            "Could we use XML or YAML instead? Yes — they are both structured formats. "
            "JSON is preferred because: (1) every LLM has seen billions of JSON examples in "
            "training and reliably produces it; (2) Python's built-in json module parses it "
            "natively; (3) it maps directly to Python dicts and Pydantic models with no "
            "conversion step; (4) it is the native format for REST APIs, ChromaDB metadata, "
            "Redis values, and Excel generation — the entire pipeline speaks JSON."
        )
    )


def section_resume_bullets(doc):
    h1(doc, "5. Resume Bullets — Copy-Paste Ready")
    para(doc, (
        "Use these bullet points directly. Each one names the concept, the tool, "
        "and the measurable outcome."
    ))
    doc.add_paragraph()
    bullets = [
        "Built a two-tier RAG pipeline combining a static YAML domain glossary (PERST#, WAFL, NVRAM, SFO) with a live internal knowledge proxy, enabling a general-purpose LLM to correctly interpret NetApp-proprietary hardware terminology in Jira bug reports",
        "Designed a Redis caching layer with SHA-256 content-addressed keys and TTL-segmented tiers (10 min / 1 hr / 24 hr), reducing repeated analysis latency from ~60s to <100ms and eliminating redundant LLM API spend for identical inputs",
        "Implemented sliding-window text chunking (600K chars, 3K overlap) with concurrent ThreadPoolExecutor dispatch, allowing BugBuddy to process Jira issues with multi-MB log attachments that exceed any single model's context window",
        "Built a ChromaDB vector store using sentence-transformers/all-MiniLM-L6-v2 embeddings (384 dims) for semantic few-shot retrieval — similar past bug analyses are dynamically injected into the LLM prompt as examples, improving test case quality on recurring bug patterns",
        "Implemented LLM-as-Judge quality scoring with a second model call (gpt-4o-mini, temperature=0.0) grading each test case on specificity, coverage, completeness and actionability — composite score surfaces in Excel export for QA team prioritisation",
        "Added input guardrails with regex-based PII redaction (email, IPv4, phone, CC) and prompt injection detection, enforced before every external LLM call in compliance with enterprise data-handling requirements",
        "Integrated Pydantic schema validation on all LLM outputs — malformed items are skipped individually rather than crashing the run; tc_number normalisation and steps coercion prevent silent downstream data quality issues",
        "Built a Server-Sent Events (SSE) streaming endpoint that pushes pipeline stage events to the browser in real time, eliminating perceived latency for multi-chunk analyses that take 30–60 seconds",
        "Designed a provider fallback chain (LLM_FALLBACK_CHAIN env var) that transparently retries failed LLM calls against backup providers, ensuring analysis completion during partial API outages",
        "Implemented structured per-call observability: every LLM inference emits a JSON trace (latency, tokens, cost estimate, cache hit, quality score) to the Python logger and an optional JSONL trace file, aggregated into a /api/stats dashboard",
    ]
    for b in bullets:
        bullet(doc, b)


def section_tech_stack(doc):
    h1(doc, "6. Technology Choices Explained")
    para(doc, (
        "For every tool, a reviewer may ask 'why this and not X?' "
        "The answers below justify each choice against the most common alternatives."
    ))
    doc.add_paragraph()
    table(doc,
        ["Component", "Tool Used", "Why This? Why Not the Alternative?"],
        [
            ["LLM access",      "openai / anthropic / google SDKs",
             "Unified provider abstraction — swap with one env var. Not LangChain because we don't need agent loops; direct SDK calls are easier to debug and have no hidden prompts."],
            ["Vector DB",       "ChromaDB (embedded)",
             "No separate server to manage. HNSW index gives O(log n) similarity search. Alternative: pgvector if already running PostgreSQL; Pinecone/Weaviate for multi-tenant cloud scale."],
            ["Embedding model", "sentence-transformers all-MiniLM-L6-v2",
             "Runs 100% locally, 384 dims, fast, no API cost. Alternative: OpenAI text-embedding-3-small for higher accuracy in cloud environments."],
            ["Cache",           "Redis",
             "In-memory, sub-millisecond reads, native TTL support, proven at scale. Alternative: Memcached (simpler but no TTL per key, no persistence)."],
            ["Output schema",   "Pydantic v2",
             "Runtime type enforcement with automatic coercion and human-readable errors. Alternative: jsonschema (more verbose, no Python object output)."],
            ["Web framework",   "Flask",
             "Lightweight, synchronous, easy to reason about. SSE streaming works natively. Alternative: FastAPI (better async, auto-docs, but heavier setup for this use case)."],
            ["Jira client",     "jira (Python)",
             "Official Atlassian-maintained SDK, handles pagination and auth. Alternative: raw requests to REST API (more control, more code)."],
            ["Doc extraction",  "pdfminer, python-docx, openpyxl",
             "Best-in-class single-purpose libraries for each format. Alternative: Apache Tika (universal, but requires a Java server process)."],
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Build + run
# ─────────────────────────────────────────────────────────────────────────────

def build_document() -> Document:
    doc = Document()
    for sec in doc.sections:
        sec.top_margin    = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.left_margin   = Cm(2.2)
        sec.right_margin  = Cm(2.2)

    cover(doc)
    section_overview(doc)
    section_full_flow(doc)
    section_data_flow_diagram(doc)
    section_interviewer_qa(doc)
    section_resume_bullets(doc)
    section_tech_stack(doc)
    return doc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true", help="Also export PDF via docx2pdf")
    parser.add_argument("--out", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    print("Building document...")
    doc = build_document()
    out = Path(args.out)
    doc.save(str(out))
    print(f"Saved: {out}")

    if args.pdf:
        pdf = out.with_suffix(".pdf")
        try:
            from docx2pdf import convert
            convert(str(out), str(pdf))
            print(f"PDF saved: {pdf}")
        except ImportError:
            print("docx2pdf not installed — run: pip install docx2pdf")
        except Exception as exc:
            print(f"PDF conversion failed: {exc}\nOpen the .docx in Word and export manually.")


if __name__ == "__main__":
    main()
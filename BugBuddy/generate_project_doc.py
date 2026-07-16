"""
generate_project_doc.py
-----------------------
Generates a polished Word (.docx) document describing the BugBuddy AI project
architecture, AI concepts, PERST# domain knowledge, and Redis caching design.

Run:
    python generate_project_doc.py
    python generate_project_doc.py --pdf      # also exports PDF via LibreOffice (if installed)

Output: BugBuddy_Project_Architecture.docx  (same directory)

Requirements:
    pip install python-docx
    pip install docx2pdf       # optional, only needed for --pdf flag
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("python-docx not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement


OUTPUT_PATH = Path(__file__).parent / "BugBuddy_Project_Architecture.docx"

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
NAVY       = RGBColor(0x00, 0x2D, 0x62)   # headings
TEAL       = RGBColor(0x00, 0x7A, 0x87)   # sub-headings
ORANGE     = RGBColor(0xE8, 0x6A, 0x10)   # accent / labels
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)
DARK_GREY  = RGBColor(0x40, 0x40, 0x40)
RED_DARK   = RGBColor(0xC0, 0x00, 0x00)
GREEN_DARK = RGBColor(0x37, 0x5A, 0x31)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_cell_bg(cell, hex_color: str) -> None:
    """Set a table cell background colour (hex without #)."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    run = p.runs[0] if p.runs else p.add_run(text)
    run.font.color.rgb = NAVY if level == 1 else TEAL
    run.font.bold = True


def _add_paragraph(doc: Document, text: str, bold: bool = False,
                   color: RGBColor | None = None, indent: float = 0) -> None:
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def _add_bullet(doc: Document, text: str, level: int = 0) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(level * 0.8 + 0.5)
    run = p.add_run(text)
    run.font.size = Pt(10.5)


def _add_code_block(doc: Document, lines: list[str]) -> None:
    """Render a monospaced code-style block using a shaded table."""
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    _set_cell_bg(cell, "1E1E1E")
    cell.paragraphs[0].clear()
    for line in lines:
        p = cell.add_paragraph()
        run = p.add_run(line)
        run.font.name = "Courier New"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xD4, 0xD4, 0xD4)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
    # remove the empty first paragraph that add_table creates
    first = cell.paragraphs[0]
    if not first.text:
        first._element.getparent().remove(first._element)


def _add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    """Add a styled table with a navy header row."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style   = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        _set_cell_bg(cell, "002D62")
        p    = cell.paragraphs[0]
        run  = p.add_run(h)
        run.font.bold  = True
        run.font.color.rgb = WHITE
        run.font.size  = Pt(10)
        p.alignment    = WD_ALIGN_PARAGRAPH.CENTER

    # Data rows
    for r_idx, row in enumerate(rows):
        bg = "F2F2F2" if r_idx % 2 == 0 else "FFFFFF"
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            _set_cell_bg(cell, bg)
            p    = cell.paragraphs[0]
            run  = p.add_run(val)
            run.font.size = Pt(10)


def _add_divider(doc: Document) -> None:
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pb  = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "007A87")
    pb.append(bottom)
    pPr.append(pb)


# ---------------------------------------------------------------------------
# Document sections
# ---------------------------------------------------------------------------

def _cover(doc: Document) -> None:
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("BugBuddy")
    run.font.size  = Pt(36)
    run.font.bold  = True
    run.font.color.rgb = NAVY

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run("AI-Powered Test Gap Analyzer")
    run2.font.size  = Pt(20)
    run2.font.color.rgb = TEAL

    doc.add_paragraph()
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run3 = p3.add_run("Production-Grade AI Project Architecture")
    run3.font.size  = Pt(14)
    run3.font.color.rgb = DARK_GREY
    run3.font.italic = True

    doc.add_paragraph()
    doc.add_paragraph()
    _add_divider(doc)


def _executive_summary(doc: Document) -> None:
    _add_heading(doc, "1. Executive Summary", 1)
    _add_paragraph(doc, (
        "BugBuddy is a production-ready, multi-provider LLM application that connects to Jira, "
        "ingests bug reports with all their attachments, enriches the LLM prompt using a two-tier "
        "RAG pipeline, and generates structured, schema-enforced test cases that would have caught "
        "each defect before it reached the field. "
        "Every expensive operation is cached in Redis so repeated analyses are served in milliseconds."
    ))
    doc.add_paragraph()
    _add_table(doc,
        ["Dimension", "Value"],
        [
            ["Domain",           "Enterprise NVMe/SAN Storage QA (NetApp ONTAP / CFSHELF)"],
            ["Core AI Pattern",  "Agentic RAG Pipeline with multi-LLM routing"],
            ["LLM Providers",    "OpenAI GPT-4o · Anthropic Claude · Google Gemini · NetApp proxy"],
            ["Caching",          "Redis — 3-tier TTL cache (Jira scrape / RAG / LLM results)"],
            ["Output Format",    "Structured JSON test cases (schema-enforced via prompt engineering)"],
            ["Document Ingest",  "PDF · DOCX · XLSX · ZIP · TAR · RTF · gzip"],
            ["Web Interface",    "Flask REST API + Excel export"],
        ]
    )


def _ai_concepts(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "2. AI Concepts Demonstrated", 1)
    _add_paragraph(doc, (
        "The table below maps each industry-standard AI engineering concept to the specific "
        "module and implementation detail within BugBuddy."
    ))
    doc.add_paragraph()
    _add_table(doc,
        ["AI Concept", "Module", "Implementation Detail"],
        [
            ["RAG — Retrieval-Augmented Generation",
             "org_rag.py",
             "First 4 000 chars of Jira text sent to internal knowledge proxy; "
             "returned glossary injected into system prompt before LLM call"],
            ["Two-tier Domain Adaptation",
             "org_context.yaml + org_rag.py",
             "Static YAML glossary (PERST#, WAFL, NVRAM, SFO…) combined with "
             "dynamic live RAG lookup — base knowledge + issue-specific enrichment"],
            ["Multi-LLM Provider Abstraction",
             "llm_agent.py — PROVIDERS dict",
             "Unified interface over OpenAI, Anthropic, Gemini, internal proxy, mock. "
             "Zero code changes required to swap provider at runtime"],
            ["Prompt Engineering & Structured Output",
             "llm_agent.py — _SYSTEM_PROMPT_BASE",
             "System prompt enforces strict JSON schema; temperature=0.2 for "
             "deterministic output; few-shot-style field descriptions"],
            ["Context Window Management / Chunking",
             "llm_agent.py — _CHUNK_SIZE_CHARS",
             "600 000-char sliding window with 3 000-char overlap — handles "
             "massive Jira threads without data loss across chunk boundaries"],
            ["Document Intelligence",
             "jira_scrubber.py",
             "Extracts text from PDF, DOCX, XLSX, ZIP, TAR.BZ2, RTF, gzip "
             "attachments automatically before LLM analysis"],
            ["Structured Data Extraction",
             "jira_filter.py — JiraQueryEngine",
             "FilterParams dataclass → JQL DSL translation with auto-discovery "
             "of custom Jira fields (Target Release, fixVersion)"],
            ["Caching Layer (Redis)",
             "cache.py — BugBuddyCache",
             "SHA-256-keyed, gzip-compressed, TTL-segmented cache: "
             "10 min scrape / 1 hr RAG / 24 hr LLM. Graceful no-Redis fallback"],
            ["Agentic Orchestration Pipeline",
             "app.py",
             "Multi-step chain: Filter → Scrape → Cache check → RAG enrich → "
             "Context build → LLM route → Chunk merge → Cache store → Export"],
            ["Output Post-processing",
             "app.py + openpyxl",
             "JSON validation, test-case merging across chunks, Excel export "
             "with formatted headers, coloured rows, and column auto-sizing"],
        ]
    )


def _architecture(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "3. System Architecture", 1)
    _add_paragraph(doc, (
        "The diagram below shows the full request flow from the user's browser "
        "through every layer of BugBuddy."
    ))
    doc.add_paragraph()

    _add_code_block(doc, [
        "┌─────────────────────────────────────────────────────────────────────────────┐",
        "│                           BugBuddy — Full Architecture                      │",
        "└─────────────────────────────────────────────────────────────────────────────┘",
        "",
        "  ┌──────────┐     Filter params      ┌──────────────────────┐",
        "  │  Browser  │ ─────────────────────► │  Flask REST API       │",
        "  │  (Web UI) │ ◄─────────────────────  │  app.py               │",
        "  └──────────┘   JSON test cases +     └──────────┬───────────┘",
        "                  Excel / DOCX export              │",
        "                                                   ▼",
        "                                        ┌──────────────────────┐",
        "                                        │  JiraQueryEngine     │",
        "                                        │  jira_filter.py      │",
        "                                        │  FilterParams → JQL  │",
        "                                        └──────────┬───────────┘",
        "                                                   │ JQL query",
        "                                                   ▼",
        "                                        ┌──────────────────────┐",
        "                                        │  Jira Server          │",
        "                                        │  (REST API)           │",
        "                                        └──────────┬───────────┘",
        "                                                   │ Raw issue + attachments",
        "                                                   ▼",
        "                                        ┌──────────────────────┐",
        "                                        │  JiraScrubber        │",
        "                                        │  jira_scrubber.py    │",
        "                                        │  PDF/DOCX/ZIP/RTF…   │",
        "                                        └──────────┬───────────┘",
        "                                                   │ full_text blob",
        "                       ┌───────────────────────────┼───────────────────────┐",
        "                       │ Cache layer               │                        │",
        "                       ▼  cache.py                 ▼                        ▼",
        "             ┌──────────────────┐       ┌──────────────────┐   ┌──────────────────┐",
        "             │  Redis           │       │  RAG Step        │   │  org_context.yaml │",
        "             │  bb:scrape:KEY   │       │  org_rag.py      │   │  Static Glossary  │",
        "             │  bb:rag:HASH     │       │  4 000-char      │   │  PERST#, WAFL,    │",
        "             │  bb:llm:HASH     │       │  excerpt →       │   │  NVRAM, SFO…      │",
        "             └────────┬─────────┘       │  Knowledge proxy │   └────────┬──────────┘",
        "              hit/miss│                 └────────┬─────────┘            │",
        "                      │                          │ glossary              │",
        "                      │               ┌──────────▼───────────────────────▼──────┐",
        "                      │               │        Context Builder                   │",
        "                      │               │  System prompt = Base + Static YAML      │",
        "                      │               │              + Live RAG glossary         │",
        "                      │               └──────────────────────┬──────────────────┘",
        "                      │                                       │ enriched prompt",
        "                      │                                       ▼",
        "                      │                          ┌────────────────────────┐",
        "                      │                          │      LLM Router        │",
        "                      │                          │    llm_agent.py        │",
        "                      │                          └──┬──┬──┬──┬──┬─────────┘",
        "                      │                          GPT│  │  │  │  │Mock",
        "                      │                    Claude───┘  │  │  └──Gemini",
        "                      │                        NetApp──┘  └────Internal",
        "                      │                                       │",
        "                      │               ┌───────────────────────▼──────────────────┐",
        "                      │               │     Chunk Merger + JSON Validator         │",
        "                      │               │  Merges results from N chunks; validates │",
        "                      │               │  schema; deduplicates TC numbers          │",
        "                      │               └──────────────────────┬───────────────────┘",
        "                      │                                       │ list[TestCase]",
        "                      └───────────────────────────────────────┘",
        "                                       Cache store (bb:llm:HASH)",
        "",
        "  Final output → Web UI display  │  Excel (.xlsx)  │  Word (.docx)  │  PDF",
    ])


def _component_details(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "4. Component Deep-Dive", 1)

    # --- JiraQueryEngine ---
    _add_heading(doc, "4.1  JiraQueryEngine  (jira_filter.py)", 2)
    _add_paragraph(doc, (
        "Translates a FilterParams dataclass — populated by the web UI — into a valid JQL "
        "string and executes it in batches of 50 issues.  Auto-discovers the 'Target Release' "
        "custom field ID on first call so the tool is not hard-coded to any single Jira instance."
    ))
    _add_bullet(doc, "Inputs: project, fix_version, issue_type, status, priority, assignee, date range, sprint, arbitrary extra JQL")
    _add_bullet(doc, "Batch size: 50 (safe for large payloads per Jira API guidance)")
    _add_bullet(doc, "Field discovery: scans all Jira fields for 'target', 'release', 'version' keywords")
    _add_bullet(doc, "Output: list of raw issue dicts passed to JiraScrubber")

    doc.add_paragraph()

    # --- JiraScrubber ---
    _add_heading(doc, "4.2  JiraScrubber  (jira_scrubber.py)", 2)
    _add_paragraph(doc, (
        "Reads a single Jira issue and extracts every piece of meaningful text: summary, "
        "description (Jira markup stripped), all comments, and the text content of every "
        "attachment up to the configured size limit (default 5 MB)."
    ))
    _add_table(doc,
        ["Attachment Type", "Extraction Method"],
        [
            ["PDF",        "pdfminer.high_level.extract_text"],
            ["DOCX",       "python-docx — paragraph extraction"],
            ["XLSX",       "openpyxl read_only — sheet-by-sheet TSV"],
            ["ZIP",        "zipfile — recursive text decode"],
            ["TAR / TBZ2", "tarfile — member-by-member extraction"],
            ["gzip",       "gzip.decompress then re-detect format"],
            ["RTF",        "striprtf.rtf_to_text"],
            ["Plain text", "UTF-8 decode with error replacement"],
        ]
    )

    doc.add_paragraph()

    # --- Redis Cache ---
    _add_heading(doc, "4.3  Redis Cache Layer  (cache.py)", 2)
    _add_paragraph(doc, (
        "Three-tier TTL-segmented cache that eliminates redundant Jira API calls, "
        "RAG proxy calls, and expensive LLM completions. "
        "All values are SHA-256 keyed, JSON-serialised, and gzip-compressed before storage."
    ))
    _add_table(doc,
        ["Cache Tier", "Key Pattern", "TTL", "Rationale"],
        [
            ["Jira Scrape",   "bb:scrape:<ISSUE-KEY>",               "10 min",
             "Issue content changes infrequently; short TTL keeps data fresh"],
            ["RAG Glossary",  "bb:rag:<sha256(text[:4000])>",        "1 hour",
             "Same text excerpt always maps to the same glossary; terminology stable"],
            ["LLM Result",    "bb:llm:<provider>:<model>:<key>:<hash>", "24 hours",
             "Temperature=0.2 makes output deterministic; expensive to regenerate"],
        ]
    )
    _add_paragraph(doc, "Graceful degradation: BugBuddy runs fully without Redis — all get/set calls are no-ops on connection failure.", color=GREEN_DARK)

    doc.add_paragraph()

    # --- RAG Step ---
    _add_heading(doc, "4.4  RAG Step  (org_rag.py)", 2)
    _add_paragraph(doc, (
        "The first 4 000 characters of the Jira issue text are sent to an internal "
        "NetApp knowledge proxy (a domain-tuned model) to identify and explain every "
        "NetApp-internal term, acronym, subsystem, or release codename in the issue. "
        "The returned bullet-list glossary is then injected into the main LLM system prompt."
    ))
    _add_code_block(doc, [
        "RAG flow:",
        "  1.  full_text[:4000]  ──►  NetApp knowledge proxy  (identifies PERST#, WAFL, SFO, etc.)",
        "  2.  proxy returns:    ──►  '• PERST#: PCI Express Reset, active-low ...'",
        "                              '• NSSR: NVM Subsystem Reset ...'",
        "  3.  glossary injected into system prompt:",
        "       '--- ORGANIZATION TERMINOLOGY (from internal knowledge proxy) ---'",
        "       '• PERST#: ...'",
        "       '--- END KNOWLEDGE CONTEXT ---'",
    ])

    doc.add_paragraph()

    # --- Context Builder ---
    _add_heading(doc, "4.5  Context Builder & Prompt Engineering  (llm_agent.py)", 2)
    _add_paragraph(doc, (
        "The system prompt is assembled from three layers, combined in order of priority:"
    ))
    _add_bullet(doc, "Layer 1 — Base prompt: role definition (senior QA engineer), task (test gap analysis), strict JSON schema with field descriptions")
    _add_bullet(doc, "Layer 2 — Static org context: org_context.yaml compiled into prompt text at load time (PERST#, WAFL, NVRAM, LIF, SFO, ACP, AGGR, RDB…)")
    _add_bullet(doc, "Layer 3 — Dynamic RAG knowledge: live glossary from org_rag.py specific to the current issue")
    _add_bullet(doc, "temperature=0.2 ensures near-deterministic output suitable for caching and comparison")

    doc.add_paragraph()

    # --- LLM Router ---
    _add_heading(doc, "4.6  LLM Router  (llm_agent.py — PROVIDERS)", 2)
    _add_paragraph(doc, (
        "A single analyse() call dispatches to the correct provider implementation based "
        "on the LLM_PROVIDER environment variable. Each provider is a thin wrapper around "
        "the vendor SDK with identical input/output contracts."
    ))
    _add_table(doc,
        ["Provider", "SDK", "Models", "Use Case"],
        [
            ["openai",    "openai",             "gpt-4o, gpt-4o-mini, gpt-4-turbo, o1", "Production — best reasoning"],
            ["netapp",    "openai (proxy URL)",  "gpt-4.1, gpt-4.1-mini, gpt-4o",       "Internal — corp network, no data egress"],
            ["anthropic", "anthropic",           "claude-3-5-sonnet, claude-3-opus",     "Alternative — long-context"],
            ["gemini",    "google-generativeai", "gemini-2.0-flash, gemini-1.5-pro",     "Cost-optimised runs"],
            ["mock",      "(none)",              "mock",                                  "CI / development / demo"],
        ]
    )

    doc.add_paragraph()

    # --- Chunking ---
    _add_heading(doc, "4.7  Context Window Management / Chunking", 2)
    _add_paragraph(doc, (
        "Large Jira issues (many comments + attachments) can exceed any model's context window. "
        "BugBuddy splits the full_text blob into chunks before sending to the LLM:"
    ))
    _add_bullet(doc, "Chunk size: 600 000 characters (~150 000 tokens) — leaves room for system prompt (~2 K tokens) and JSON response (~4 K tokens)")
    _add_bullet(doc, "Overlap: 3 000 characters repeated at the start of each chunk — prevents context loss at boundaries")
    _add_bullet(doc, "Each chunk is analysed independently; results are merged and TC numbers re-sequenced")
    _add_bullet(doc, "Single-issue issues skip chunking entirely for latency efficiency")


def _perst_section(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "5. Domain Knowledge: PERST# (PCIe Reset Signal)", 1)

    _add_paragraph(doc, (
        "PERST# is a fundamental hardware concept in the NVMe storage domain that BugBuddy "
        "must understand to generate accurate test cases for PCIe-related bugs. "
        "It is now codified in org_context.yaml and automatically injected into every LLM prompt."
    ))

    doc.add_paragraph()
    _add_heading(doc, "5.1  What is PERST#?", 2)
    _add_paragraph(doc, (
        "PERST# stands for PCI Express Reset. The # suffix means the signal is active-low: "
        "the device is held in reset when the signal is at logic 0 (ground) and released "
        "from reset when the signal goes HIGH."
    ))

    _add_code_block(doc, [
        "  Host (Root Complex)  ──── PERST# pin ────►  Endpoint (NVMe SSD / GPU / NIC)",
        "       drives the signal                        receives the signal",
        "",
        "  PCIe slot pin: B22",
        "  U.2 connector: dedicated PERST# pin in SFF-8639",
        "  M.2 connector: Pin 6",
    ])

    doc.add_paragraph()
    _add_heading(doc, "5.2  Analogy", 2)
    _add_paragraph(doc, (
        "Think of PERST# as the power button on a game console. "
        "While you hold it down (signal LOW), the console is completely off and unresponsive. "
        "The moment you release it (signal HIGH), the console starts its full boot sequence — "
        "firmware loads, hardware initializes, everything from scratch. "
        "PERST# does exactly that to a PCIe device."
    ))

    doc.add_paragraph()
    _add_heading(doc, "5.3  Reset Sequence After PERST# Deasserted (HIGH)", 2)
    _add_code_block(doc, [
        "  PERST# goes HIGH",
        "      └──► PCIe LTSSM starts from Detect state",
        "                └──► Polling → Configuration → L0 (link up)",
        "                          └──► Firmware loads from flash",
        "                                    └──► NVMe controller initializes",
        "                                              └──► Volume open sequence",
        "                                                        └──► Namespace metadata read",
        "                                                                  └──► CSTS.RDY = 1",
        "                                                                            └──► Controller READY",
    ])
    _add_paragraph(doc, (
        "This is why PERST# recovery is the slowest of all PCIe reset types — "
        "every layer from the physical link upward must be rebuilt from scratch."
    ))

    doc.add_paragraph()
    _add_heading(doc, "5.4  Reset Type Comparison", 2)
    _add_table(doc,
        ["Reset Type", "PCIe Link Down?", "Firmware Reload?", "Relative Speed", "Trigger"],
        [
            ["PERST#",     "YES",  "YES", "Slowest",   "Host pin assertion / power cycle"],
            ["Hot Reset",  "YES",  "YES", "Slow",      "TS1 ordered sets in-band"],
            ["FLR",        "NO",   "NO",  "Fast",      "PCI function-level reset register"],
            ["NSSR",       "NO",   "YES", "Medium",    "NVMe CC.SHN / NSSR register write"],
        ]
    )

    doc.add_paragraph()
    _add_heading(doc, "5.5  When PERST# Fires in Practice", 2)
    _add_table(doc,
        ["Scenario", "Why PERST# Fires"],
        [
            ["System power cycle",        "Host de-powers and re-powers the PCIe slot"],
            ["Cold boot",                 "Host holds all endpoints in reset during early BIOS init"],
            ["PCIe hot-plug remove",      "Slot controller asserts PERST# on physical removal"],
            ["OS-level surprise removal", "Host asserts PERST# to force clean endpoint shutdown"],
            ["Error recovery",            "Host uses PERST# as last-resort after failed FLR / link-down recovery"],
            ["Drive power cycle in test", "Bench power supply toggling drive Vcc also toggles PERST#"],
        ]
    )

    doc.add_paragraph()
    _add_heading(doc, "5.6  Connection to the NSSR Dual-Port Corruption Bug", 2)
    _add_paragraph(doc, (
        "Understanding PERST# is critical for diagnosing the class of bugs BugBuddy targets. "
        "In the NSSR dual-port corruption scenario:"
    ), bold=False)
    _add_bullet(doc, "Normal NSSR recovery does NOT require PERST# — the controller resets internally and comes back without the PCIe link going down")
    _add_bullet(doc, "When NSSR corrupted metadata, the volume open sequence FAILED during firmware initialization after the subsequent PERST# (drive power cycle)")
    _add_bullet(doc, "The controller never reached CSTS.RDY = 1 — so it never signalled PCIe link UP")
    _add_bullet(doc, "Result: host saw zero device on the bus (absent from lspci) — not a PHY failure, but a firmware initialization failure post-reset")

    _add_code_block(doc, [
        "  PERST# deasserted (power cycle after NSSR corruption)",
        "      └──► LTSSM trains to L0  ✓",
        "                └──► Firmware loads  ✓",
        "                          └──► Volume open → reads metadata → CORRUPTED  ✗",
        "                                    └──► Controller stuck — never reaches CSTS.RDY = 1",
        "                                              └──► PCIe link never asserted UP",
        "                                                        └──► Host: device NOT found (lspci empty)",
        "",
        "  Root cause: metadata corruption during NSSR, exposed only after PERST# (power cycle)",
        "  Detection gap: no test exercised dual-port NSSR followed by drive power cycle + lspci check",
    ])


def _redis_detail(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "6. Redis Caching — Design Details", 1)

    _add_paragraph(doc, (
        "Redis sits between every expensive external call and the core BugBuddy pipeline. "
        "Without cache a single analysis takes 15–60 seconds (Jira + RAG + LLM). "
        "With cache a repeated analysis on the same issue returns in under 100 ms."
    ))

    doc.add_paragraph()
    _add_heading(doc, "6.1  Cache Key Design", 2)
    _add_code_block(doc, [
        "  Jira scrape:   bb:scrape:<ISSUE-KEY>                    e.g.  bb:scrape:CFSHELF-4291",
        "  RAG glossary:  bb:rag:<sha256(full_text[:4000])>        content-addressed",
        "  LLM result:    bb:llm:<provider>:<model>:<key>:<sha256(full_text)>",
        "                 e.g.  bb:llm:openai:gpt-4o:CFSHELF-4291:a3f2...",
    ])

    doc.add_paragraph()
    _add_heading(doc, "6.2  Value Encoding", 2)
    _add_code_block(doc, [
        "  value = gzip.compress( json.dumps(python_object).encode('utf-8') )",
        "",
        "  Benefits:",
        "    - JSON: human-inspectable via redis-cli, language-agnostic",
        "    - gzip: reduces storage by 70-85% for text-heavy Jira content",
        "    - Combined: a 50 KB full_text blob compresses to ~8 KB in Redis",
    ])

    doc.add_paragraph()
    _add_heading(doc, "6.3  TTL Strategy", 2)
    _add_table(doc,
        ["Tier", "TTL", "Why This Value"],
        [
            ["Jira scrape",  "600 s  (10 min)",  "Engineers update comments/attachments frequently; short TTL prevents stale analysis"],
            ["RAG glossary", "3600 s (1 hr)",    "Org terminology barely changes; longer TTL reduces knowledge proxy load"],
            ["LLM result",   "86400 s (24 hr)",  "Deterministic at temperature=0.2; same input = same output. Expensive to regenerate"],
        ]
    )

    doc.add_paragraph()
    _add_heading(doc, "6.4  Graceful Degradation", 2)
    _add_paragraph(doc, (
        "All cache operations are wrapped in try/except. If Redis is down, "
        "unavailable, or misconfigured:"
    ))
    _add_bullet(doc, "BugBuddy continues operating at full functionality — just slower")
    _add_bullet(doc, "cache.available returns False; cache.stats() returns {\"available\": False}")
    _add_bullet(doc, "Connection timeout is capped at 2 seconds to avoid blocking the request thread")
    _add_bullet(doc, "Socket timeout on every read/write is also 2 seconds")


def _resume_section(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "7. Resume Description", 1)

    _add_heading(doc, "Project Title", 2)
    _add_paragraph(doc,
        "BugBuddy — Agentic AI Test Gap Analyzer  |  Python · Flask · LLM · RAG · Redis",
        bold=True, color=NAVY)

    doc.add_paragraph()
    _add_heading(doc, "Project Description (3-4 lines)", 2)
    _add_paragraph(doc, (
        "Built a production-ready LLM application that ingests Jira bug reports (including PDF, DOCX, "
        "ZIP and TAR attachments) and automatically generates structured test cases that would have "
        "caught each defect before it reached production. Implemented a two-tier RAG pipeline: a "
        "static YAML domain glossary (PERST#, WAFL, NVRAM, SFO…) combined with a live internal "
        "knowledge proxy that annotates org-specific terminology before each LLM call. "
        "Supports hot-swappable LLM providers (OpenAI GPT-4o, Anthropic Claude, Google Gemini, "
        "internal proxy) through a unified abstraction. All expensive operations are cached in Redis "
        "with TTL-segmented, content-addressed, gzip-compressed keys — reducing repeated analysis "
        "latency from 60 s to under 100 ms."
    ))

    doc.add_paragraph()
    _add_heading(doc, "Bullet Points", 2)
    bullets = [
        "Designed a two-tier RAG architecture combining a static YAML domain knowledge base "
        "(PERST#, WAFL, NVRAM, SFO, ACP) with a live internal knowledge proxy, reducing "
        "LLM hallucinations on proprietary storage terminology",
        "Implemented a Redis caching layer with SHA-256-keyed, gzip-compressed, TTL-segmented "
        "tiers (10 min / 1 hr / 24 hr) for Jira data, RAG glossaries, and LLM results — "
        "reducing repeat-analysis latency from ~60 s to <100 ms",
        "Built a multi-provider LLM abstraction supporting OpenAI GPT-4o, Anthropic Claude, "
        "Google Gemini, and an internal corporate proxy — zero code changes to swap providers",
        "Implemented a document intelligence pipeline that extracts text from PDF, DOCX, XLSX, "
        "ZIP, TAR, and RTF attachments, enabling full-evidence analysis of bug reproduction logs",
        "Applied context window management with 600 K-char sliding-window chunking and 3 K-char "
        "overlap, handling Jira issues exceeding any single model's context limit without data loss",
        "Enforced schema-validated JSON output via prompt engineering at temperature=0.2, producing "
        "machine-parseable test cases (tc_number, title, gap_reason, steps, expected, test_type) "
        "suitable for direct import into test management tools",
        "Codified PCIe hardware knowledge (PERST# reset sequence, LTSSM states, CSTS.RDY semantics) "
        "into the org context, enabling accurate root-cause test gap analysis for NVMe firmware bugs",
    ]
    for b in bullets:
        _add_bullet(doc, b)


def _production_additions(doc: Document) -> None:
    doc.add_paragraph()
    _add_heading(doc, "8. Recommended Production Enhancements", 1)
    _add_paragraph(doc, (
        "The following additions would further demonstrate production AI engineering depth "
        "in an interview setting:"
    ))
    doc.add_paragraph()
    _add_table(doc,
        ["Enhancement", "AI Concept", "Effort"],
        [
            ["Vector DB (ChromaDB / Pinecone) for past analyses",     "Semantic Search, Embeddings",      "Medium"],
            ["LangGraph orchestration with conditional routing",       "Agentic Frameworks, Graphs",       "High"],
            ["Server-Sent Events (SSE) for streaming LLM responses",  "LLM Streaming",                    "Low"],
            ["LLM-as-judge scoring of generated test cases",          "LLM Evaluation, Self-critique",     "Medium"],
            ["Prometheus metrics + Grafana cache hit-rate dashboard",  "MLOps / Observability",            "Medium"],
            ["Docker Compose (Flask + Redis + optional Milvus)",       "Containerization, MLOps",          "Low"],
            ["GitHub Actions CI: mock-provider regression tests",      "CI/CD for AI pipelines",           "Low"],
            ["Fine-tuned embedding model for org terminology",         "Domain Fine-tuning",               "High"],
        ]
    )


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_document() -> Document:
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.2)
        section.right_margin  = Cm(2.2)

    _cover(doc)
    _executive_summary(doc)
    _ai_concepts(doc)
    _architecture(doc)
    _component_details(doc)
    _perst_section(doc)
    _redis_detail(doc)
    _resume_section(doc)
    _production_additions(doc)

    return doc


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate BugBuddy project architecture document")
    parser.add_argument("--pdf", action="store_true",
                        help="Also export a PDF using docx2pdf (requires LibreOffice or MS Word)")
    parser.add_argument("--out", default=str(OUTPUT_PATH),
                        help=f"Output .docx path (default: {OUTPUT_PATH})")
    args = parser.parse_args()

    print("Building document...")
    doc = build_document()
    out_path = Path(args.out)
    doc.save(str(out_path))
    print(f"Saved: {out_path}")

    if args.pdf:
        pdf_path = out_path.with_suffix(".pdf")
        try:
            from docx2pdf import convert  # noqa: PLC0415
            convert(str(out_path), str(pdf_path))
            print(f"Saved PDF: {pdf_path}")
        except ImportError:
            print("docx2pdf not installed — run:  pip install docx2pdf")
            print("Or open the .docx in Word and export as PDF manually.")
        except Exception as exc:
            print(f"PDF conversion failed: {exc}")
            print("Open the .docx in Word / LibreOffice and export as PDF.")


if __name__ == "__main__":
    main()

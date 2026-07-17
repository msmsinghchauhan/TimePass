"""
app.py
------
Flask web application – the BugBuddy GUI.

Start:
    python app.py

Then open:  http://localhost:5000

Environment variables (or edit JIRA_* constants below):
    JIRA_SERVER       Jira base URL
    JIRA_TOKEN        Personal Access Token
    OPENAI_API_KEY    OpenAI direct key
    NETAPP_LLM_KEY    NetApp internal LLM proxy key
    ANTHROPIC_API_KEY Anthropic key
    GOOGLE_API_KEY    Google Gemini key
    LLM_PROVIDER      openai | netapp | anthropic | gemini | mock  (default: mock)
    LLM_MODEL         model name override (defaults to first model for provider)
    LLM_FALLBACK_CHAIN  comma-separated fallback providers e.g. "openai,anthropic"
    REDIS_URL         Redis connection URL (default: redis://localhost:6379/0)
    CHROMA_PERSIST_DIR  ChromaDB storage dir (default: ./chroma_store/)
    EMBED_PROVIDER    sentence | openai | mock  (default: sentence)
    JUDGE_PROVIDER    LLM-as-Judge provider  (default: openai)
    JUDGE_MODEL       LLM-as-Judge model     (default: gpt-4o-mini)
    TRACE_FILE        Optional path to JSONL observability trace file
"""

from __future__ import annotations

import io
import os
import json
import threading

from flask import Flask, Response, jsonify, render_template, request, send_file, session, stream_with_context
from jira import JIRA
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from jira_filter import FilterParams, JiraQueryEngine
from jira_scrubber import JiraScrubber
from llm_agent import LLMAgent, PROVIDERS, load_org_context, _ORG_CONTEXT_PATH
from org_rag import get_config as get_org_knowledge_config
from cache import BugBuddyCache
from observability import tracer
from embeddings import SemanticMemory
from models import TestCaseFeedback

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JIRA_SERVER  = os.getenv("JIRA_SERVER",  "https://jira.ngage.netapp.com")
JIRA_TOKEN   = os.getenv("JIRA_TOKEN",   "ODQ2Mzc5NzIwMTMxOmlV9HWBWemi4GuzntuAG3lh1Sy8")
SECRET_KEY   = os.getenv("SECRET_KEY",   "bugbuddy-dev-secret-change-in-prod")

# Server-side LLM configuration — set these in .env, not in the UI
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
LLM_MODEL    = os.getenv("LLM_MODEL", "") or None

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------------------------------------------------------------------------
# Shared Jira / LLM / cache / memory singletons (lazy init)
# ---------------------------------------------------------------------------

_jira_client:  JIRA | None              = None
_engine:       JiraQueryEngine | None   = None
_scrubber:     JiraScrubber | None      = None
_cache:        BugBuddyCache | None     = None
_memory:       SemanticMemory | None    = None


def _get_jira() -> JIRA:
    global _jira_client
    if _jira_client is None:
        _jira_client = JIRA(server=JIRA_SERVER, token_auth=JIRA_TOKEN)
    return _jira_client


def _get_cache() -> BugBuddyCache:
    global _cache
    if _cache is None:
        _cache = BugBuddyCache()
    return _cache


def _get_memory() -> SemanticMemory:
    global _memory
    if _memory is None:
        _memory = SemanticMemory()
    return _memory


def _get_engine() -> JiraQueryEngine:
    global _engine
    if _engine is None:
        _engine = JiraQueryEngine(server=JIRA_SERVER, token=JIRA_TOKEN)
    return _engine


def _get_scrubber() -> JiraScrubber:
    global _scrubber
    if _scrubber is None:
        _scrubber = JiraScrubber(_get_jira())
    return _scrubber


def _make_llm() -> LLMAgent:
    """Instantiate LLMAgent from server-side environment configuration only."""
    cfg     = PROVIDERS.get(LLM_PROVIDER, {})
    key_env = cfg.get("key_env", "")
    api_key = os.getenv(key_env, "") if key_env else ""
    return LLMAgent(
        provider=LLM_PROVIDER,
        api_key=api_key,
        model=LLM_MODEL,
        org_knowledge_key=os.getenv("ORG_KNOWLEDGE_KEY") or None,
    )


# ---------------------------------------------------------------------------
# Helper: fetch dropdown values from Jira
# ---------------------------------------------------------------------------

_ALLOWED_PROJECTS = {"CFSHELF", "CFBRIDGE", "CONTAP", "CFLOADER", "CFBIOS", "CLP", "CCLP"}

def _fetch_meta() -> dict:
    """Return lists of possible values for filter dropdowns."""
    jira = _get_jira()
    projects   = sorted([p.key for p in jira.projects() if p.key in _ALLOWED_PROJECTS])
    priorities = [p.name for p in jira.priorities()]
    statuses   = list({s.name for s in jira.statuses()})
    issue_types = list({it.name for it in jira.issue_types()})
    return {
        "projects":    projects,
        "priorities":  priorities,
        "statuses":    sorted(statuses),
        "issue_types": sorted(issue_types),
    }


def _fetch_versions(project: str) -> list[str]:
    jira = _get_jira()
    try:
        versions = jira.project_versions(project)
        return sorted([v.name for v in versions], reverse=True)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Excel export helper
# ---------------------------------------------------------------------------

def _build_excel(issue_key: str, test_cases: list[dict]) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"

    header_font    = Font(bold=True, color="FFFFFF")
    header_fill    = PatternFill("solid", fgColor="1F4E79")
    wrap_alignment = Alignment(wrap_text=True, vertical="top")

    headers = ["TC#", "Title", "Jira Key", "Test Type", "Gap Reason",
               "Pre-conditions", "Test Steps", "Expected Result"]
    col_widths = [8, 40, 14, 14, 45, 35, 60, 40]

    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = wrap_alignment
        ws.column_dimensions[cell.column_letter].width = w

    for row_idx, tc in enumerate(test_cases, 2):
        steps_text = "\n".join(tc.get("steps", []))
        values = [
            tc.get("tc_number", ""),
            tc.get("title", ""),
            issue_key,
            tc.get("test_type", ""),
            tc.get("gap_reason", ""),
            tc.get("preconditions", ""),
            steps_text,
            tc.get("expected", ""),
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.alignment = wrap_alignment
        ws.row_dimensions[row_idx].height = max(60, len(steps_text) // 2)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    try:
        meta = _fetch_meta()
    except Exception as exc:
        meta = {"projects": [], "priorities": [], "statuses": [], "issue_types": [],
                "error": str(exc)}
    return render_template("index.html", meta=meta)


@app.route("/api/versions")
def api_versions():
    """Return fix versions for the selected project (called via AJAX)."""
    project = request.args.get("project", "")
    if not project:
        return jsonify([])
    return jsonify(_fetch_versions(project))


@app.route("/api/components")
def api_components():
    """Return components for the selected project (called via AJAX)."""
    project = request.args.get("project", "")
    if not project:
        return jsonify([])
    try:
        jira = _get_jira()
        comps = jira.project_components(project)
        return jsonify(sorted([c.name for c in comps]))
    except Exception:
        return jsonify([])


@app.route("/api/debug-parent")
def api_debug_parent():
    """Debug: show raw parent field of an issue. Usage: /api/debug-parent?key=CFSHELF-1234"""
    key = request.args.get("key", "").strip().upper()
    if not key:
        return jsonify({"error": "key param required"}), 400
    try:
        jira = _get_jira()
        issue = jira.issue(key, fields="summary,issuetype,parent,subtasks")
        raw_fields = issue.raw.get("fields", {})
        return jsonify({
            "key": key,
            "summary": raw_fields.get("summary", ""),
            "issuetype": raw_fields.get("issuetype", {}).get("name", ""),
            "issuetype_subtask": raw_fields.get("issuetype", {}).get("subtask", False),
            "parent_raw": raw_fields.get("parent"),
            "subtasks_raw": [s.get("key") for s in (raw_fields.get("subtasks") or [])],
            "fields_present": list(raw_fields.keys()),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/search", methods=["POST"])
def api_search():
    """Execute a Jira filter query; return list of matching issues."""
    data = request.get_json(force=True)

    def _listify(v):
        if not v:
            return None
        return v if isinstance(v, list) else [v]

    params = FilterParams(
        project          = data.get("project") or None,
        fix_version      = data.get("fix_version") or None,
        target_release   = data.get("target_release") or None,
        issue_type       = _listify(data.get("issue_type")),
        status           = _listify(data.get("status")),
        priority         = _listify(data.get("priority")),
        assignee         = data.get("assignee") or None,
        reporter         = data.get("reporter") or None,
        labels           = [l.strip() for l in (data.get("labels") or "").split(",") if l.strip()],
        components       = _listify(data.get("components")),
        summary_contains = data.get("summary_contains") or None,
        keyword          = data.get("keyword") or None,
        created_after    = data.get("created_after") or None,
        created_before   = data.get("created_before") or None,
        updated_after    = data.get("updated_after") or None,
        updated_before   = data.get("updated_before") or None,
        sprint           = data.get("sprint") or None,
        extra_jql        = data.get("extra_jql") or None,
        max_results      = int(data.get("max_results") or 200),
        order_by         = data.get("order_by") or "created DESC",
    )

    engine = _get_engine()
    jql    = engine.build_jql(params)
    parent_mode = bool(data.get("parent_mode"))

    import sys
    print(f"[SEARCH] parent_mode={parent_mode} jql={jql[:120]}", file=sys.stderr, flush=True)

    try:
        if parent_mode:
            issues = engine.query_parent_issues(params)
            print(f"[SEARCH] parent_mode results: {[i['key'] for i in issues]}", file=sys.stderr, flush=True)
            print(f"[SEARCH] matched_subtasks: { {i['key']: i.get('matched_subtasks',[]) for i in issues} }", file=sys.stderr, flush=True)
        else:
            issues = engine.query_from_params(params)
        # store keys in session so we can paginate/export later
        session["last_issue_keys"] = [i["key"] for i in issues]
        return jsonify({"jql": jql, "total": len(issues), "issues": issues,
                        "parent_mode": parent_mode,
                        "_debug": {"matched_subtasks_counts":
                                   {i["key"]: i.get("matched_subtasks", [])
                                    for i in issues}} if parent_mode else {}})
    except Exception as exc:
        import traceback
        print(f"[SEARCH ERROR] {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": str(exc), "jql": jql}), 400


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Scrub a single Jira issue and generate test cases via LLM.

    Accepted body fields:
        issue_key   (required)  Jira issue key, e.g. CFSHELF-5078
        provider    (optional)  Override LLM_PROVIDER env var
        model       (optional)  Override LLM_MODEL env var
        api_key     (optional)  Override the provider's key env var

    If provider/model/api_key are omitted, falls back to server-side
    environment variables (LLM_PROVIDER, LLM_MODEL, NETAPP_LLM_KEY /
    OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY).
    """
    data      = request.get_json(force=True)
    issue_key = (data.get("issue_key") or "").strip().upper()
    if not issue_key:
        return jsonify({"error": "issue_key is required"}), 400

    # include_parent=true → also fetch parent Jira for richer context
    include_parent = bool(data.get("include_parent", True))

    # Allow per-request override of provider/model/key; fall back to server env
    req_provider = (data.get("provider") or "").strip().lower() or LLM_PROVIDER
    req_model    = (data.get("model") or "").strip() or LLM_MODEL or None
    req_api_key  = (data.get("api_key") or "").strip()
    if not req_api_key:
        cfg     = PROVIDERS.get(req_provider, {})
        key_env = cfg.get("key_env", "")
        req_api_key = os.getenv(key_env, "") if key_env else ""

    try:
        scrubber = _get_scrubber()
        scraped  = (scrubber.scrub_with_parent(issue_key)
                    if include_parent else scrubber.scrub(issue_key))
        llm = LLMAgent(
            provider=req_provider,
            api_key=req_api_key or None,
            model=req_model,
            org_knowledge_key=os.getenv("ORG_KNOWLEDGE_KEY") or None,
        )
        test_cases = llm.generate_test_cases(scraped, scrubber)
        session[f"tc_{issue_key}"] = test_cases
        parent_key = scraped.get("parent_key")
        return jsonify({
            "issue_key":   issue_key,
            "summary":     scraped["summary"],
            "url":         scraped["url"],
            "provider":    req_provider,
            "model":       llm.model,
            "parent_key":  parent_key,
            "test_cases":  test_cases,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/export/<issue_key>")
def api_export(issue_key: str):
    """Download the generated test cases as an Excel file."""
    issue_key  = issue_key.strip().upper()
    test_cases = session.get(f"tc_{issue_key}")
    if not test_cases:
        return jsonify({"error": "No test cases found. Run analysis first."}), 404

    buf = _build_excel(issue_key, test_cases)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"TestCases_{issue_key}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/export-batch", methods=["POST"])
def api_export_batch():
    """Download all analyzed issues in one Excel workbook (one sheet per issue + Summary sheet)."""
    body = request.get_json(force=True) or {}
    keys = [k.strip().upper() for k in (body.get("keys") or []) if k.strip()]
    if not keys:
        return jsonify({"error": "No keys provided"}), 400

    wb = Workbook()
    header_font  = Font(bold=True, color="FFFFFF")
    header_fill  = PatternFill("solid", fgColor="1F4E79")
    wrap_align   = Alignment(wrap_text=True, vertical="top")
    headers      = ["TC#", "Title", "Jira Key", "Test Type", "Gap Reason",
                    "Pre-conditions", "Test Steps", "Expected Result"]
    col_widths   = [8, 40, 14, 14, 45, 35, 60, 40]

    # Summary sheet
    ws_sum = wb.active
    ws_sum.title = "Summary"
    sum_headers = ["Jira Key", "Summary (truncated)", "# Test Cases", "Types"]
    for ci, h in enumerate(sum_headers, 1):
        c = ws_sum.cell(row=1, column=ci, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = wrap_align
    ws_sum.column_dimensions["A"].width = 16
    ws_sum.column_dimensions["B"].width = 60
    ws_sum.column_dimensions["C"].width = 14
    ws_sum.column_dimensions["D"].width = 40
    sum_row = 2

    found_any = False
    for issue_key in keys:
        test_cases = session.get(f"tc_{issue_key}")
        if not test_cases:
            continue
        found_any = True

        # Per-issue sheet
        ws = wb.create_sheet(title=issue_key[:31])  # Excel sheet name ≤31 chars
        for ci, (h, w) in enumerate(zip(headers, col_widths), 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.font = header_font; cell.fill = header_fill; cell.alignment = wrap_align
            ws.column_dimensions[cell.column_letter].width = w

        for ri, tc in enumerate(test_cases, 2):
            steps_text = "\n".join(tc.get("steps", []))
            vals = [tc.get("tc_number",""), tc.get("title",""), issue_key,
                    tc.get("test_type",""), tc.get("gap_reason",""),
                    tc.get("preconditions",""), steps_text, tc.get("expected","")]
            for ci, v in enumerate(vals, 1):
                cell = ws.cell(row=ri, column=ci, value=v)
                cell.alignment = wrap_align
            ws.row_dimensions[ri].height = max(40, len(steps_text) // 2)

        # Summary row
        types = ", ".join(sorted({tc.get("test_type","") for tc in test_cases if tc.get("test_type")}))
        ws_sum.cell(row=sum_row, column=1, value=issue_key).alignment = wrap_align
        ws_sum.cell(row=sum_row, column=2, value=test_cases[0].get("title","")[:100] if test_cases else "").alignment = wrap_align
        ws_sum.cell(row=sum_row, column=3, value=len(test_cases)).alignment = wrap_align
        ws_sum.cell(row=sum_row, column=4, value=types).alignment = wrap_align
        sum_row += 1

    if not found_any:
        return jsonify({"error": "No session data found for any of the provided keys. Re-run analysis first."}), 404

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    label = "_".join(keys[:4]) + ("_etc" if len(keys) > 4 else "")
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"TestCases_Batch_{label}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/org-knowledge-config")
def api_org_knowledge_config():
    """Return the current org knowledge proxy configuration (no secrets)."""
    cfg = get_org_knowledge_config()
    return jsonify(cfg)


# ---------------------------------------------------------------------------
# Org context  –  GET to read, POST to save
# ---------------------------------------------------------------------------

@app.route("/api/context", methods=["GET"])
def api_context_get():
    """Return the current org_context.yaml as plain text."""
    try:
        text = _ORG_CONTEXT_PATH.read_text(encoding="utf-8") if _ORG_CONTEXT_PATH.exists() else ""
        return jsonify({"content": text})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/context", methods=["POST"])
def api_context_save():
    """Save edited org_context.yaml and bust the in-memory cache."""
    body = request.get_json(force=True) or {}
    content = body.get("content", "")
    try:
        # Validate it's parseable YAML before saving
        import yaml
        yaml.safe_load(content)
        _ORG_CONTEXT_PATH.write_text(content, encoding="utf-8")
        # Bust the cache so next analysis uses the new file
        load_org_context(force_reload=True)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ---------------------------------------------------------------------------
# New AI-layer endpoints
# ---------------------------------------------------------------------------

@app.route("/api/stream-analyse")
def api_stream_analyse():
    """SSE endpoint — streams pipeline progress events so the UI can show a live progress bar
    instead of a spinner. Runs the same pipeline as the regular analyse endpoint.

    Query params: issue_key (required)
    Event format: data: {"stage": "rag"|"llm"|"done"|"error", ...}
    """
    issue_key = request.args.get("issue_key", "").strip().upper()
    if not issue_key:
        return jsonify({"error": "issue_key required"}), 400

    def generate():
        def _emit(stage: str, **kwargs) -> str:
            payload = json.dumps({"stage": stage, **kwargs})
            return f"data: {payload}\n\n"

        try:
            yield _emit("start", message=f"Starting analysis for {issue_key}")

            # Cache check
            cache = _get_cache()
            cached = cache.get_llm(LLM_PROVIDER, LLM_MODEL or "", issue_key, issue_key)
            if cached:
                yield _emit("cache_hit", message="Returning cached result")
                yield _emit("done", test_cases=cached)
                return

            # Jira scrape
            yield _emit("scrape", message="Fetching Jira issue and attachments...")
            scrubber = _get_scrubber()
            scraped  = scrubber.scrub(issue_key)

            # RAG
            yield _emit("rag", message="Running RAG terminology lookup...")

            # LLM
            yield _emit("llm", message=f"Calling {LLM_PROVIDER} ({LLM_MODEL or 'default'})...")
            agent = _make_llm()
            test_cases = agent.generate_test_cases(scraped, scrubber)

            # Evaluation
            yield _emit("evaluate", message="Running LLM-as-Judge quality scoring...")

            # Cache store
            cache.set_llm(LLM_PROVIDER, LLM_MODEL or "", issue_key,
                          issue_key, test_cases)

            yield _emit("done", test_cases=test_cases)

        except Exception as exc:
            yield _emit("error", message=str(exc))

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """Store user ratings on generated test cases back to ChromaDB metadata.
    Ratings can later be used to weight retrieval in few-shot selection.

    Body: {"issue_key": "CFSHELF-1234", "tc_number": "TC-001", "rating": 5, "comment": ""}
    """
    try:
        data = request.get_json(force=True) or {}
        feedback = TestCaseFeedback.model_validate(data)
        feedback.provider = LLM_PROVIDER
        feedback.model    = LLM_MODEL or ""
        # Store feedback in memory metadata
        memory = _get_memory()
        if memory.available:
            memory._collection.update(
                ids=[feedback.issue_key],
                metadatas=[{
                    "last_rating":   feedback.rating,
                    "rating_comment": feedback.comment[:200],
                }],
            )
        return jsonify({"status": "ok", "feedback": feedback.model_dump()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/stats")
def api_stats():
    """Aggregated metrics since server start: cache hit rate, avg latency,
    token usage, estimated cost, quality scores, calls by provider.
    """
    obs   = tracer.get_stats()
    cache = _get_cache().stats()
    mem   = _get_memory().stats()
    return jsonify({
        "llm_calls":    obs,
        "cache":        cache,
        "vector_store": mem,
        "providers":    list(PROVIDERS.keys()),
    })


@app.route("/api/stats/recent")
def api_stats_recent():
    """Return the 20 most recent LLM call trace records."""
    n = min(int(request.args.get("n", 20)), 100)
    return jsonify(tracer.recent(n))


@app.route("/api/cache/invalidate", methods=["POST"])
def api_cache_invalidate():
    """Force-evict a cached result so the next request re-runs the full pipeline.

    Body JSON: {"issue_key": "CFSHELF-1234", "tier": "all|scrape|llm|rag"}
    """
    data      = request.get_json(force=True) or {}
    issue_key = data.get("issue_key", "").strip().upper()
    tier      = data.get("tier", "all").lower()
    if not issue_key:
        return jsonify({"error": "issue_key required"}), 400

    cache  = _get_cache()
    evicted: list[str] = []
    if tier in ("all", "scrape"):
        cache.invalidate_scrape(issue_key)
        evicted.append("scrape")
    if tier in ("all", "llm"):
        cache.invalidate_llm(LLM_PROVIDER, LLM_MODEL or "", issue_key, issue_key)
        evicted.append("llm")

    return jsonify({"issue_key": issue_key, "evicted_tiers": evicted})


@app.route("/api/similar")
def api_similar():
    """Find semantically similar past analyses for an issue using vector search.
    Query params: issue_key (required), top_k (default 3)
    """
    issue_key = request.args.get("issue_key", "").strip().upper()
    top_k     = int(request.args.get("top_k", 3))
    if not issue_key:
        return jsonify({"error": "issue_key required"}), 400

    try:
        scrubber = _get_scrubber()
        scraped  = scrubber.scrub(issue_key)
        text     = scrubber.full_text(scraped)
        memory   = _get_memory()
        similar  = memory.retrieve_similar(text, top_k=top_k)
        return jsonify({"issue_key": issue_key, "similar": similar})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)

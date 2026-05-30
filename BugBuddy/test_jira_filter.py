"""
test_jira_filter.py
-------------------
CLI test harness for jira_filter.py – no GUI required.

Run:
    python test_jira_filter.py

Each TEST_* function exercises a different aspect of the module.
Pass --test <name> to run only one test, e.g.:
    python test_jira_filter.py --test jql_builder
    python test_jira_filter.py --test live_query
"""

import argparse
import json
import sys
from typing import Optional
from jira_filter import FilterParams, JiraQueryEngine

# ---------------------------------------------------------------------------
# Connection config – edit these before running
# ---------------------------------------------------------------------------
JIRA_SERVER = "https://jira.ngage.netapp.com"
JIRA_TOKEN  = "ODQ2Mzc5NzIwMTMxOmlV9HWBWemi4GuzntuAG3lh1Sy8"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_issues(issues: list[dict], limit: int = 10) -> None:
    if not issues:
        print("  [no results]")
        return
    print(f"  Total returned: {len(issues)}  (showing up to {limit})\n")
    for i, issue in enumerate(issues[:limit], 1):
        print(f"  {i:>3}. [{issue['key']}] {issue['summary']}")
        print(f"       Status: {issue['status']}  |  Priority: {issue['priority']}"
              f"  |  Assignee: {issue['assignee']}")
        print(f"       Fix versions: {issue['fix_versions']}  |  Created: {issue['created']}")
        print(f"       URL: {issue['url']}")
        print()


# ---------------------------------------------------------------------------
# TEST 1 – JQL builder (offline, no network call)
# ---------------------------------------------------------------------------

def test_jql_builder() -> None:
    _section("TEST: JQL builder (no network)")

    cases = [
        FilterParams(project="CFSHELF"),
        FilterParams(project="CFSHELF", fix_version="3.14"),
        FilterParams(
            project="CFSHELF",
            fix_version="3.14",
            status=["Open", "In Progress"],
            priority=["Critical", "Blocker"],
        ),
        FilterParams(
            project="CFSHELF",
            assignee="john.doe",
            labels=["regression", "nightly"],
            summary_contains="crash",
            created_after="2025-01-01",
        ),
        FilterParams(
            extra_jql='cf[10200] = "some custom field"',
            order_by="updated DESC",
        ),
    ]

    # We only need build_jql – create a dummy engine (connection is lazy)
    engine = JiraQueryEngine.__new__(JiraQueryEngine)
    engine._server = JIRA_SERVER

    for params in cases:
        jql = engine.build_jql(params)
        print(f"  Params : {params}")
        print(f"  JQL    : {jql}\n")

    print("  [PASS] JQL builder")


# ---------------------------------------------------------------------------
# TEST 2 – Live query: single project, small result set
# ---------------------------------------------------------------------------

def test_live_query(engine: JiraQueryEngine) -> None:
    _section("TEST: live_query – project=CFSHELF, max 5 results")

    issues = engine.query(
        project="CFSHELF",
        max_results=5,
        order_by="created DESC",
    )
    _print_issues(issues)

    assert isinstance(issues, list), "Expected a list"
    if issues:
        required_keys = {"key", "url", "summary", "status", "priority",
                         "assignee", "reporter", "fix_versions", "created"}
        missing = required_keys - issues[0].keys()
        assert not missing, f"Missing keys in result dict: {missing}"
    print("  [PASS] live_query")


# ---------------------------------------------------------------------------
# TEST 3 – Live query with status + priority filters
# ---------------------------------------------------------------------------

def test_filtered_query(engine: JiraQueryEngine) -> None:
    _section("TEST: filtered_query – project=CFSHELF, status=Open, priority=Critical|Blocker")

    issues = engine.query(
        project="CFSHELF",
        status="Open",
        priority=["Critical", "Blocker"],
        max_results=10,
    )
    _print_issues(issues)
    print("  [PASS] filtered_query")


# ---------------------------------------------------------------------------
# TEST 4 – Live query using FilterParams directly
# ---------------------------------------------------------------------------

def test_filter_params_object(engine: JiraQueryEngine) -> None:
    _section("TEST: filter_params_object – using FilterParams dataclass")

    params = FilterParams(
        project="CFSHELF",
        issue_type="Bug",
        max_results=5,
        order_by="updated DESC",
    )

    # Show the JQL before running
    jql = engine.get_jql(params)
    print(f"  Generated JQL: {jql}\n")

    issues = engine.query_from_params(params)
    _print_issues(issues)
    print("  [PASS] filter_params_object")


# ---------------------------------------------------------------------------
# TEST 5 – Target release filter: glenmo.041x
# ---------------------------------------------------------------------------

def test_target_release(engine: JiraQueryEngine,
                        target_release: str = "glenmo.041x",
                        project: Optional[str] = None,
                        labels: Optional[list] = None,
                        keyword: Optional[str] = None) -> None:
    title = f"TEST: target_release = '{target_release}'"
    if project:
        title += f", project = '{project}'"
    if labels:
        title += f", labels = {labels}"
    if keyword:
        title += f", keyword = '{keyword}'"
    _section(title)

    # Step 1 – show which field is used for target_release
    resolved = engine._resolve_target_release_field()
    print(f"  TARGET_RELEASE_FIELD = '{resolved}'")

    # Step 2 – build and show JQL
    params = FilterParams(
        project=project,
        target_release=target_release,
        labels=labels or [],
        keyword=keyword,
        max_results=500,
        order_by="created DESC",
    )
    jql = engine.get_jql(params)
    print(f"  Generated JQL: {jql}\n")

    # Step 3 – run query
    try:
        issues = engine.query_from_params(params)
        _print_issues(issues, limit=len(issues))
        print(f"  [PASS] target_release  ({len(issues)} issue(s) found)")
    except Exception as exc:
        print(f"  [FAIL] Query failed: {exc}")
        print("\n  HINT: Set the correct field ID manually before querying:")
        print("    from jira_filter import JiraQueryEngine")
        print("    JiraQueryEngine.TARGET_RELEASE_FIELD = '<correct field id>'")
        print(f"    engine.query(target_release='{target_release}')")


# ---------------------------------------------------------------------------
# TEST 6 – JSON serialisation (sanity check for GUI consumption)
# ---------------------------------------------------------------------------

def test_json_serialisable(engine: JiraQueryEngine) -> None:
    _section("TEST: json_serialisable – result can be serialised to JSON")

    issues = engine.query(project="CFSHELF", max_results=3)
    try:
        payload = json.dumps(issues, indent=2)
        print(payload[:800], "...\n" if len(payload) > 800 else "")
        print("  [PASS] json_serialisable")
    except TypeError as exc:
        print(f"  [FAIL] json_serialisable – {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

ALL_TESTS = {
    "jql_builder":          (test_jql_builder, False),   # (fn, needs_engine)
    "live_query":           (test_live_query, True),
    "filtered_query":       (test_filtered_query, True),
    "filter_params_object": (test_filter_params_object, True),
    "target_release":       (test_target_release, True),
    "json_serialisable":    (test_json_serialisable, True),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Test jira_filter.py without a GUI")
    parser.add_argument(
        "--test", "-t",
        choices=list(ALL_TESTS.keys()),
        default=None,
        help="Run only this test (default: run all)",
    )
    parser.add_argument(
        "--jql-only",
        action="store_true",
        help="Only run the offline JQL builder test (no network needed)",
    )
    parser.add_argument(
        "--project", "-p",
        default=None,
        help="Filter results by Jira project key, e.g. CFSHELF (used by target_release test)",
    )
    parser.add_argument(
        "--target-release", "-r",
        default="glenmo.041x",
        help="Target release value to query (default: glenmo.041x)",
    )
    parser.add_argument(
        "--label", "-l",
        action="append",
        dest="labels",
        default=None,
        help="Filter by label (repeatable: -l bug -l regression)",
    )
    parser.add_argument(
        "--keyword", "-k",
        default=None,
        help="Full-text keyword search across summary, description and comments",
    )
    args = parser.parse_args()

    selected = list(ALL_TESTS.keys())
    if args.jql_only:
        selected = ["jql_builder"]
    elif args.test:
        selected = [args.test]

    # Build engine once (only if any live test is needed)
    needs_engine = any(ALL_TESTS[t][1] for t in selected)
    engine = None
    if needs_engine:
        print(f"Connecting to {JIRA_SERVER} …")
        try:
            engine = JiraQueryEngine(server=JIRA_SERVER, token=JIRA_TOKEN)
            print("  Connected.\n")
        except Exception as exc:
            print(f"  [ERROR] Could not connect to Jira: {exc}")
            sys.exit(1)

    for name in selected:
        fn, req_engine = ALL_TESTS[name]
        try:
            if name == "target_release":
                fn(engine, target_release=args.target_release,
                   project=args.project, labels=args.labels, keyword=args.keyword)
            elif req_engine:
                fn(engine)
            else:
                fn()
        except Exception as exc:
            print(f"\n  [FAIL] {name} raised: {exc}")
            import traceback; traceback.print_exc()

    print("\nAll selected tests finished.")


if __name__ == "__main__":
    main()

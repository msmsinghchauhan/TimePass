"""
jira_filter.py
--------------
Module for fetching Jira issues based on filter parameters supplied by a
frontend GUI.  The GUI collects user input and calls JiraQueryEngine.query()
(or passes a FilterParams dataclass to JiraQueryEngine.query_from_params()).
Results are returned as plain Python dicts so the GUI can render them freely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from jira import JIRA


# ---------------------------------------------------------------------------
# Filter parameter container
# ---------------------------------------------------------------------------

@dataclass
class FilterParams:
    """All supported Jira filter parameters.

    GUI frontend should populate whichever fields the user fills in and leave
    the rest as None / empty list.  All string values are treated as exact
    matches unless they contain a wildcard (*).
    """

    # Core filters
    project: Optional[str] = None           # e.g. "CFSHELF"
    fix_version: Optional[str] = None       # Jira fixVersion field
    target_release: Optional[str] = None    # Target Release (fixVersion or custom field)
    issue_type: Optional[Union[str, List[str]]] = None  # Bug, Story, Task …
    status: Optional[Union[str, List[str]]] = None      # Open, In Progress …
    priority: Optional[Union[str, List[str]]] = None    # Blocker, Critical …

    # People
    assignee: Optional[str] = None          # Jira username or display name
    reporter: Optional[str] = None

    # Categorisation
    labels: List[str] = field(default_factory=list)   # match ALL listed labels
    components: Optional[Union[str, List[str]]] = None

    # Text search
    summary_contains: Optional[str] = None  # searches summary field only
    keyword: Optional[str] = None           # searches summary + description + comments (text ~)

    # Date range (ISO format: "YYYY-MM-DD")
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    updated_after: Optional[str] = None
    updated_before: Optional[str] = None

    # Sprint (name or id)
    sprint: Optional[str] = None

    # Arbitrary extra JQL to AND-append (advanced / power-user field)
    extra_jql: Optional[str] = None

    # Result controls
    max_results: int = 200
    order_by: str = "created DESC"


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------

class JiraQueryEngine:
    """Connects to a Jira instance and executes filtered queries.

    Parameters
    ----------
    server:
        Full URL of the Jira server, e.g. "https://jira.example.com"
    token:
        Personal Access Token (PAT) for token-based auth.
    """

    # "Target Release" custom field on jira.ngage.netapp.com (customfield_21440)
    # Change this if you connect to a different Jira instance.
    TARGET_RELEASE_FIELD: str = '"Target Release"'

    # Fields fetched for every issue (keeps payloads small)
    _DEFAULT_FIELDS = [
        "summary", "status", "priority", "assignee", "reporter",
        "issuetype", "fixVersions", "components", "labels",
        "created", "updated", "description", "subtasks", "parent",
        "comment",
    ]
    _BATCH_SIZE = 50   # Jira recommends ≤ 100; 50 is safe for large payloads

    # Keywords used to identify "Target Release" among all Jira custom fields
    _RELEASE_FIELD_KEYWORDS = ["target release", "targetrelease", "target_release"]

    def __init__(self, server: str, token: str) -> None:
        self._server = server.rstrip("/")
        self._jira = JIRA(server=self._server, token_auth=token)
        self._target_release_field: str | None = None  # resolved lazily

    # ------------------------------------------------------------------
    # Field discovery
    # ------------------------------------------------------------------

    def discover_release_fields(self) -> list[dict]:
        """Return all Jira fields whose name contains 'release', 'version', or 'target'.

        Useful for finding the correct field ID when target_release queries fail.
        Call this once and print the results to identify the right field name/ID.
        """
        keywords = ["target", "release", "version", "fix"]
        found = []
        for f in self._jira.fields():
            if any(kw in f["name"].lower() for kw in keywords):
                found.append({"id": f["id"], "name": f["name"]})
        return found

    def _resolve_target_release_field(self) -> str:
        """Auto-detect the field ID for 'Target Release'.

        Resolution order:
        1. Already resolved and cached → return cached value.
        2. CLASS-LEVEL override set (TARGET_RELEASE_FIELD != 'fixVersion') → use it.
        3. Search all Jira fields for a name matching _RELEASE_FIELD_KEYWORDS.
        4. Fall back to 'fixVersion'.
        """
        if self._target_release_field:
            return self._target_release_field

        # Class-level override already set by caller
        if self.TARGET_RELEASE_FIELD != "fixVersion":
            self._target_release_field = self.TARGET_RELEASE_FIELD
            return self._target_release_field

        # Auto-discover
        for f in self._jira.fields():
            if f["name"].lower() in self._RELEASE_FIELD_KEYWORDS:
                self._target_release_field = f["id"]
                return self._target_release_field

        # Fallback
        self._target_release_field = "fixVersion"
        return self._target_release_field

    def build_jql(self, params: FilterParams) -> str:
        """Translate a FilterParams object into a JQL string."""
        clauses: list[str] = []

        def _quote(v: str) -> str:
            # Escape double-quotes inside the value
            return '"' + v.replace('"', '\\"') + '"'

        def _in_or_eq(field_name: str, value: Union[str, List[str]]) -> str:
            if isinstance(value, list) and len(value) > 1:
                values = ", ".join(_quote(v) for v in value)
                return f"{field_name} in ({values})"
            single = value[0] if isinstance(value, list) else value
            return f'{field_name} = {_quote(single)}'

        if params.project:
            clauses.append(f'project = {_quote(params.project)}')

        if params.fix_version:
            clauses.append(f'fixVersion = {_quote(params.fix_version)}')

        if params.target_release:
            field_id = self._resolve_target_release_field()
            clauses.append(f'{field_id} = {_quote(params.target_release)}')

        if params.issue_type:
            clauses.append(_in_or_eq("issuetype", params.issue_type))

        if params.status:
            clauses.append(_in_or_eq("status", params.status))

        if params.priority:
            clauses.append(_in_or_eq("priority", params.priority))

        if params.assignee:
            clauses.append(f'assignee = {_quote(params.assignee)}')

        if params.reporter:
            clauses.append(f'reporter = {_quote(params.reporter)}')

        for label in params.labels:
            clauses.append(f'labels = {_quote(label)}')

        if params.components:
            clauses.append(_in_or_eq("component", params.components))

        if params.summary_contains:
            clauses.append(f'summary ~ {_quote(params.summary_contains)}')

        if params.keyword:
            # text ~ searches summary, description, comments, and other text fields
            clauses.append(f'text ~ {_quote(params.keyword)}')

        if params.created_after:
            clauses.append(f'created >= {_quote(params.created_after)}')
        if params.created_before:
            clauses.append(f'created <= {_quote(params.created_before)}')
        if params.updated_after:
            clauses.append(f'updated >= {_quote(params.updated_after)}')
        if params.updated_before:
            clauses.append(f'updated <= {_quote(params.updated_before)}')

        if params.sprint:
            clauses.append(f'sprint = {_quote(params.sprint)}')

        if params.extra_jql:
            clauses.append(f'({params.extra_jql})')

        jql = " AND ".join(clauses)
        if params.order_by:
            jql += f" ORDER BY {params.order_by}"

        return jql

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _fetch_all(self, jql: str, max_results: int) -> list:
        """Paginate through Jira results and return all matching issues."""
        issues: list = []
        start_at = 0

        while len(issues) < max_results:
            batch_size = min(self._BATCH_SIZE, max_results - len(issues))
            batch = self._jira.search_issues(
                jql,
                startAt=start_at,
                maxResults=batch_size,
                fields=",".join(self._DEFAULT_FIELDS),
            )
            issues.extend(batch)
            if len(batch) < batch_size or start_at + len(batch) >= batch.total:
                break
            start_at += len(batch)

        return issues

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query_from_params(self, params: FilterParams) -> list[dict]:
        """Fetch Jira issues matching the supplied FilterParams.

        Returns a list of dicts, one per issue, ready for GUI display.
        """
        jql = self.build_jql(params)
        raw_issues = self._fetch_all(jql, params.max_results)
        return self._serialize(raw_issues)

    def query_parent_issues(self, params: FilterParams) -> list[dict]:
        """Fetch the parent (master) Jira issues whose subtasks match params.

        Workflow:
          1. Run the JQL from params to get matching subtasks / child issues.
          2. For each result that has a parent, collect the unique parent keys.
          3. Fetch full details for those parents and return them.
          Issues that have no parent are returned directly (they are already
          top-level masters with subtasks).

        Returns a list of dicts (same structure as query_from_params), with an
        extra key:
            matched_subtasks: list[str]  — child keys from this parent that
                                           matched the filter.
        """
        jql = self.build_jql(params)
        raw_issues = self._fetch_all(jql, params.max_results)

        # Split into: issues that have a parent vs. already top-level
        parent_to_children: dict[str, list[str]] = {}
        top_level: list = []

        for issue in raw_issues:
            parent_key = self._extract_parent_key(issue)

            # Fallback: if issuetype.subtask == True but raw JSON had no parent field,
            # do an explicit single-issue re-fetch to get the parent key reliably.
            if not parent_key:
                is_subtask = getattr(getattr(issue.fields, "issuetype", None), "subtask", False)
                if is_subtask:
                    try:
                        refetched = self._jira.issue(issue.key, fields="parent,summary")
                        parent_key = self._extract_parent_key(refetched)
                    except Exception:
                        pass

            if parent_key:
                parent_to_children.setdefault(parent_key, []).append(issue.key)
            else:
                top_level.append(issue)

        # Fetch unique parents in batches via JQL "key in (...)"
        parent_results: list[dict] = []
        parent_keys = list(parent_to_children.keys())
        for i in range(0, len(parent_keys), self._BATCH_SIZE):
            chunk = parent_keys[i: i + self._BATCH_SIZE]
            keys_jql = "key in (" + ", ".join(chunk) + ") ORDER BY created DESC"
            raw_parents = self._jira.search_issues(
                keys_jql,
                maxResults=len(chunk),
                fields=",".join(self._DEFAULT_FIELDS),
            )
            for p in raw_parents:
                d = self._serialize([p])[0]
                d["matched_subtasks"] = parent_to_children.get(p.key, [])
                parent_results.append(d)

        # Also include top-level issues that directly matched (already masters)
        for issue in top_level:
            d = self._serialize([issue])[0]
            # If this issue itself has subtasks, list them
            subtask_keys = [s.key for s in (getattr(issue.fields, "subtasks", None) or [])]
            d["matched_subtasks"] = subtask_keys
            parent_results.append(d)

        return parent_results

    def _extract_parent_key(self, issue) -> str | None:
        """Reliably extract the parent issue key from a Jira issue object.

        jira-python's attribute access (.fields.parent) can silently return None
        even when parent data exists in the raw JSON, so we read raw JSON first.
        """
        # Method 1: raw JSON (most reliable — works for all Jira project types)
        raw_fields = issue.raw.get("fields", {}) if hasattr(issue, "raw") else {}
        raw_parent = raw_fields.get("parent") or {}
        if raw_parent.get("key"):
            return raw_parent["key"]

        # Method 2: jira-python attribute fallback
        parent_attr = getattr(issue.fields, "parent", None)
        if parent_attr and getattr(parent_attr, "key", None):
            return parent_attr.key

        return None

    def query(
        self,
        *,
        project: Optional[str] = None,
        fix_version: Optional[str] = None,
        target_release: Optional[str] = None,
        issue_type: Optional[Union[str, List[str]]] = None,
        status: Optional[Union[str, List[str]]] = None,
        priority: Optional[Union[str, List[str]]] = None,
        assignee: Optional[str] = None,
        reporter: Optional[str] = None,
        labels: Optional[List[str]] = None,
        components: Optional[Union[str, List[str]]] = None,
        summary_contains: Optional[str] = None,
        keyword: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        updated_after: Optional[str] = None,
        updated_before: Optional[str] = None,
        sprint: Optional[str] = None,
        extra_jql: Optional[str] = None,
        max_results: int = 200,
        order_by: str = "created DESC",
    ) -> list[dict]:
        """Keyword-argument convenience wrapper around query_from_params.

        GUI code can call this directly without constructing a FilterParams:

            engine.query(project="CFSHELF", fix_version="3.14", status="Open")
        """
        params = FilterParams(
            project=project,
            fix_version=fix_version,
            target_release=target_release,
            issue_type=issue_type,
            status=status,
            priority=priority,
            assignee=assignee,
            reporter=reporter,
            labels=labels or [],
            components=components,
            summary_contains=summary_contains,
            keyword=keyword,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            sprint=sprint,
            extra_jql=extra_jql,
            max_results=max_results,
            order_by=order_by,
        )
        return self.query_from_params(params)

    def get_jql(self, params: FilterParams) -> str:
        """Return the JQL string without executing the query.
        Useful for showing the user what query will be run."""
        return self.build_jql(params)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _serialize(self, issues: list) -> list[dict]:
        """Convert raw Jira issue objects into plain dicts."""
        result = []
        for issue in issues:
            f = issue.fields
            result.append({
                "key": issue.key,
                "url": f"{self._server}/browse/{issue.key}",
                "summary": f.summary or "",
                "issue_type": f.issuetype.name if f.issuetype else "",
                "status": f.status.name if f.status else "",
                "priority": f.priority.name if f.priority else "",
                "assignee": f.assignee.displayName if f.assignee else "Unassigned",
                "reporter": f.reporter.displayName if f.reporter else "",
                "fix_versions": [v.name for v in f.fixVersions] if f.fixVersions else [],
                "components": [c.name for c in f.components] if f.components else [],
                "labels": list(f.labels) if f.labels else [],
                "created": str(f.created)[:10] if f.created else "",
                "updated": str(f.updated)[:10] if f.updated else "",
            })
        return result

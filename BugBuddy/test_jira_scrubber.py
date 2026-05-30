"""
test_jira_scrubber.py
---------------------
CLI test harness for jira_scrubber.JiraScrubber.

Takes one Jira issue key, scrubs all comments and attachments,
then prints a structured report.

Usage
-----
    python test_jira_scrubber.py CFSHELF-5078
    python test_jira_scrubber.py CFSHELF-5078 --full-text
    python test_jira_scrubber.py CFSHELF-5078 --attachment-preview 300
"""

import argparse
import os
import sys
import textwrap

from jira import JIRA

from jira_scrubber import JiraScrubber

# ---------------------------------------------------------------------------
# Connection defaults (override via env vars)
# ---------------------------------------------------------------------------
JIRA_SERVER = os.getenv("JIRA_SERVER", "https://jira.ngage.netapp.com")
JIRA_TOKEN  = os.getenv("JIRA_TOKEN",  "ODQ2Mzc5NzIwMTMxOmlV9HWBWemi4GuzntuAG3lh1Sy8")

DIVIDER  = "=" * 72
DIVIDER2 = "-" * 72


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _preview(text: str, max_chars: int) -> str:
    """Return first max_chars of text, with a trailing ellipsis if truncated."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + f"\n  … [{len(text) - max_chars} more chars truncated]"


def _wrap(text: str, width: int = 90, indent: str = "  ") -> str:
    """Word-wrap text at `width` with leading `indent`."""
    if not text.strip():
        return f"{indent}(empty)"
    lines = []
    for paragraph in text.splitlines():
        if paragraph.strip():
            lines.extend(textwrap.wrap(paragraph, width=width,
                                       initial_indent=indent,
                                       subsequent_indent=indent))
        else:
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrub a single Jira issue and print all comments + attachments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python test_jira_scrubber.py CFSHELF-5078
          python test_jira_scrubber.py CFSHELF-5078 --full-text
          python test_jira_scrubber.py CFSHELF-5078 --attachment-preview 1000
          JIRA_SERVER=https://mycompany.atlassian.net python test_jira_scrubber.py PROJ-123
        """),
    )
    parser.add_argument("issue_key", help="Jira issue key, e.g. CFSHELF-5078")
    parser.add_argument(
        "--full-text", action="store_true",
        help="Print the complete flattened text (as seen by the LLM agent)"
    )
    parser.add_argument(
        "--attachment-preview", type=int, default=0, metavar="CHARS",
        help="Max characters to show per attachment (default: 0 = full; set to truncate display)"
    )
    parser.add_argument(
        "--comment-preview", type=int, default=0, metavar="CHARS",
        help="Max characters to show per comment body (default: 0 = full; set to truncate display)"
    )
    parser.add_argument(
        "--max-attachment-mb", type=float, default=5.0, metavar="MB",
        help="Skip attachments larger than this many MB (default: 5)"
    )
    args = parser.parse_args()

    issue_key = args.issue_key.strip().upper()
    att_preview  = args.attachment_preview  if args.attachment_preview  > 0 else None
    com_preview  = args.comment_preview     if args.comment_preview     > 0 else None
    max_att_bytes = int(args.max_attachment_mb * 1024 * 1024)

    # ------------------------------------------------------------------ connect
    print(f"\n{DIVIDER}")
    print(f"  Connecting to {JIRA_SERVER} …")
    try:
        jira = JIRA(server=JIRA_SERVER, token_auth=JIRA_TOKEN)
    except Exception as exc:
        print(f"  ERROR: could not connect to Jira: {exc}", file=sys.stderr)
        sys.exit(1)
    print("  Connected.")

    # ------------------------------------------------------------------ scrub
    print(f"  Scrubbing {issue_key} …")
    scrubber = JiraScrubber(jira, max_attachment_bytes=max_att_bytes)
    try:
        data = scrubber.scrub(issue_key)
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------ header
    print(f"\n{DIVIDER}")
    print("  ISSUE METADATA")
    print(DIVIDER)
    print(f"  Key         : {data['key']}")
    print(f"  URL         : {data['url']}")
    print(f"  Summary     : {data['summary']}")
    print(f"  Type        : {data['issue_type']}")
    print(f"  Status      : {data['status']}")
    print(f"  Priority    : {data['priority']}")
    print(f"  Assignee    : {data['assignee']}")
    print(f"  Reporter    : {data['reporter']}")
    print(f"  Fix Versions: {', '.join(data['fix_versions']) or '—'}")
    print(f"  Target Rel  : {data['target_release'] or '—'}")

    # ------------------------------------------------------------------ description
    print(f"\n{DIVIDER2}")
    print("  DESCRIPTION")
    print(DIVIDER2)
    print(_wrap(data["description"]) if data["description"] else "  (no description)")

    # ------------------------------------------------------------------ comments
    comments = data["comments"]
    print(f"\n{DIVIDER2}")
    print(f"  COMMENTS  ({len(comments)} total)")
    print(DIVIDER2)
    if not comments:
        print("  (no comments)")
    else:
        for idx, c in enumerate(comments, 1):
            print(f"\n  [{idx}/{len(comments)}]  {c['created']}  –  {c['author']}")
            body = _preview(c["body"], com_preview) if com_preview else c["body"].strip()
            print(_wrap(body))

    # ------------------------------------------------------------------ attachments
    attachments = data["attachments"]
    print(f"\n{DIVIDER2}")
    print(f"  ATTACHMENTS  ({len(attachments)} total)")
    print(DIVIDER2)
    if not attachments:
        print("  (no attachments)")
    else:
        for idx, a in enumerate(attachments, 1):
            content_len = len(a["content"])
            print(f"\n  [{idx}/{len(attachments)}]  {a['filename']}  ({content_len:,} chars extracted)")
            preview = _preview(a["content"], att_preview) if att_preview else a["content"].strip()
            print(_wrap(preview))

    # ------------------------------------------------------------------ summary stats
    print(f"\n{DIVIDER}")
    print("  SUMMARY")
    print(DIVIDER)
    total_text = len(data["description"]) \
               + sum(len(c["body"]) for c in comments) \
               + sum(len(a["content"]) for a in attachments)
    print(f"  Description   : {len(data['description']):>7,} chars")
    print(f"  Comments      : {len(comments):>3}  total  /  "
          f"{sum(len(c['body']) for c in comments):>7,} chars")
    print(f"  Attachments   : {len(attachments):>3}  total  /  "
          f"{sum(len(a['content']) for a in attachments):>7,} chars")
    print(f"  Grand total   : {total_text:>7,} chars of text extracted")
    print(DIVIDER)

    # ------------------------------------------------------------------ full text dump
    if args.full_text:
        print(f"\n{'#' * 72}")
        print("  FULL FLATTENED TEXT (as seen by LLM agent)")
        print(f"{'#' * 72}\n")
        print(scrubber.full_text(data))

    print()


if __name__ == "__main__":
    main()

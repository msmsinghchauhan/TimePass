"""
test_llm_agent.py
-----------------
End-to-end CLI: scrub one Jira issue → send to LLM → print test gap analysis.

Usage
-----
    # Mock (no API key needed)
    python test_llm_agent.py CFSHELF-5078

    # NetApp internal proxy (recommended on corp network)
    NETAPP_LLM_KEY=<your-key> python test_llm_agent.py CFSHELF-5078 --provider netapp
    NETAPP_LLM_KEY=<your-key> python test_llm_agent.py CFSHELF-5078 --provider netapp --model gpt-4.1-mini

    # OpenAI direct
    OPENAI_API_KEY=sk-... python test_llm_agent.py CFSHELF-5078 --provider openai
    OPENAI_API_KEY=sk-... python test_llm_agent.py CFSHELF-5078 --provider openai --model gpt-4-turbo

    # Anthropic Claude
    ANTHROPIC_API_KEY=sk-ant-... python test_llm_agent.py CFSHELF-5078 --provider anthropic

    # Google Gemini
    GOOGLE_API_KEY=AIza... python test_llm_agent.py CFSHELF-5078 --provider gemini

    # Show the full text sent to the LLM
    python test_llm_agent.py CFSHELF-5078 --show-input
"""

import argparse
import os
import sys
import textwrap

from jira import JIRA

from jira_scrubber import JiraScrubber
from llm_agent import LLMAgent, PROVIDERS

# ---------------------------------------------------------------------------
# Connection defaults (override via env vars)
# ---------------------------------------------------------------------------
JIRA_SERVER = os.getenv("JIRA_SERVER", "https://jira.ngage.netapp.com")
JIRA_TOKEN  = os.getenv("JIRA_TOKEN",  "ODQ2Mzc5NzIwMTMxOmlV9HWBWemi4GuzntuAG3lh1Sy8")

DIVIDER  = "=" * 72
DIVIDER2 = "-" * 72

TYPE_LABELS = {
    "Functional":   "FUNC",
    "Regression":   "REGR",
    "Negative":     "NEG ",
    "Performance":  "PERF",
    "Boundary":     "BNDR",
}


def _wrap(text: str, width: int = 88, indent: str = "    ") -> str:
    if not text or not text.strip():
        return f"{indent}(none)"
    lines = []
    for para in text.splitlines():
        if para.strip():
            lines.extend(textwrap.wrap(para, width=width,
                                       initial_indent=indent,
                                       subsequent_indent=indent))
        else:
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrub a Jira issue and generate test gap analysis via LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python test_llm_agent.py CFSHELF-5078
          python test_llm_agent.py CFSHELF-5078 --provider openai
          python test_llm_agent.py CFSHELF-5078 --provider openai --model gpt-4-turbo
          python test_llm_agent.py CFSHELF-5078 --provider anthropic
          python test_llm_agent.py CFSHELF-5078 --provider gemini
          python test_llm_agent.py CFSHELF-5078 --provider openai --show-input
        """),
    )
    parser.add_argument("issue_key", help="Jira issue key, e.g. CFSHELF-5078")
    parser.add_argument(
        "--provider", default=os.getenv("LLM_PROVIDER", "mock"),
        choices=list(PROVIDERS.keys()),
        help="LLM provider  (default: mock).  Available: "
             + ", ".join(f"{k} [{v['label']}]" for k, v in PROVIDERS.items())
    )
    parser.add_argument(
        "--model", default=os.getenv("LLM_MODEL", ""),
        help="Model override. Defaults to the first model for the chosen provider.\n"
             + "\n".join(f"  {k}: {', '.join(v['models'])}" for k, v in PROVIDERS.items())
    )
    parser.add_argument(
        "--api-key", default="",
        help="API key override. If omitted, uses the provider's env var "
             "(OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY)."
    )
    parser.add_argument(
        "--show-input", action="store_true",
        help="Print the full text sent to the LLM before showing results"
    )
    args = parser.parse_args()

    issue_key = args.issue_key.strip().upper()

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
    scrubber = JiraScrubber(jira)
    try:
        scraped = scrubber.scrub(issue_key)
    except Exception as exc:
        print(f"  ERROR scrubbing issue: {exc}", file=sys.stderr)
        sys.exit(1)

    full_text = scrubber.full_text(scraped)
    n_comments    = len(scraped["comments"])
    n_attachments = len(scraped["attachments"])
    n_chars       = len(full_text)
    print(f"  Scraped: {n_comments} comment(s), {n_attachments} attachment(s), "
          f"{n_chars:,} chars total.")

    # ------------------------------------------------------------------ optionally show LLM input
    if args.show_input:
        print(f"\n{'#' * 72}")
        print("  TEXT SENT TO LLM")
        print(f"{'#' * 72}\n")
        print(full_text)
        print(f"\n{'#' * 72}\n")

    # ------------------------------------------------------------------ LLM
    print(f"  Sending to LLM ({args.provider}) …")
    # Resolve API key: explicit flag > env var for the provider
    key_env = PROVIDERS[args.provider].get("key_env", "")
    api_key = args.api_key or (os.getenv(key_env, "") if key_env else "")
    agent = LLMAgent(
        provider=args.provider,
        api_key=api_key or None,
        model=args.model or None,
    )
    print(f"  Model: {agent.model}")
    try:
        test_cases = agent.generate_test_cases(scraped, scrubber)
    except Exception as exc:
        import traceback
        print(f"  ERROR from LLM: {exc}", file=sys.stderr)
        print("\n  --- Full traceback ---", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # ------------------------------------------------------------------ print results
    print(f"\n{DIVIDER}")
    print(f"  ISSUE: {scraped['key']}  —  {scraped['summary']}")
    print(f"  URL  : {scraped['url']}")
    print(DIVIDER)
    print(f"\n  {len(test_cases)} test gap(s) identified\n")

    for tc in test_cases:
        ttype = TYPE_LABELS.get(tc.get("test_type", ""), tc.get("test_type", "")[:4].upper())
        print(f"{DIVIDER2}")
        print(f"  [{ttype}]  {tc.get('tc_number', '')}  |  {tc.get('title', '')}")
        print(f"{DIVIDER2}")

        gap = tc.get("gap_reason", "")
        if gap:
            print(f"\n  WHY THIS TEST WAS MISSING:")
            print(_wrap(gap))

        pre = tc.get("preconditions", "")
        if pre:
            print(f"\n  PRE-CONDITIONS:")
            print(_wrap(pre))

        steps = tc.get("steps", [])
        if steps:
            print(f"\n  TEST STEPS:")
            for s in steps:
                print(f"    {s}")

        expected = tc.get("expected", "")
        if expected:
            print(f"\n  EXPECTED RESULT:")
            print(_wrap(expected))

        print()

    print(DIVIDER)
    print(f"  Done. {len(test_cases)} test case(s) generated for {issue_key}.")
    print(DIVIDER)
    print()


if __name__ == "__main__":
    main()

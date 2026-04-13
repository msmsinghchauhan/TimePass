#!/usr/bin/env python3
"""
setup_env.py — BugBuddy environment setup & validation
=======================================================

Automates:
  1. Python version check (3.10+)
  2. pip install / upgrade all required packages
  3. Create .env from .env.template if it does not exist
  4. Validate that required env vars are set (warn only — never fails)
  5. Quick connectivity smoke-test against the configured Jira server

USAGE
-----
  python setup_env.py              # install + validate (recommended first run)
  python setup_env.py --install    # install/upgrade packages only
  python setup_env.py --validate   # validate config only (no pip install)
  python setup_env.py --check      # alias for --validate

SERVER-SIDE LLM CONFIGURATION
------------------------------
BugBuddy reads all LLM provider settings from server-side environment variables.
Users cannot select a provider or supply keys through the web UI — all of this
is configured once by the server administrator in the .env file.

Required settings (update .env before first run):

  # ──────────── Jira ───────────────────────────────────────────────
  JIRA_SERVER=https://jira.ngage.netapp.com
  JIRA_TOKEN=<your-personal-access-token>

  # ──────────── LLM provider (choose ONE) ───────────────────────────

  # Option A — NetApp internal LLM proxy (recommended for NetApp employees)
  LLM_PROVIDER=netapp
  LLM_MODEL=gpt-4.1
  NETAPP_LLM_KEY=<key-from-https://llm-proxy-api.ai.eng.netapp.com>

  # Option B — OpenAI direct
  # LLM_PROVIDER=openai
  # LLM_MODEL=gpt-4o
  # OPENAI_API_KEY=sk-...

  # Option C — Anthropic
  # LLM_PROVIDER=anthropic
  # LLM_MODEL=claude-3-5-sonnet-20241022
  # ANTHROPIC_API_KEY=sk-ant-...

  # Option D — Google Gemini
  # LLM_PROVIDER=gemini
  # LLM_MODEL=gemini-1.5-pro
  # GOOGLE_API_KEY=AIza...

  # Option E — Mock (no key needed, returns placeholder data — for testing)
  # LLM_PROVIDER=mock

  # ──────────── Org Knowledge proxy (optional) ──────────────────────
  # When set, BugBuddy makes an extra call to explain NetApp-specific terms
  # before running the main analysis. Uses a separate internal proxy.
  ORG_KNOWLEDGE_KEY=<key-from-https://llm-proxy-web.ai.openeng.netapp.com>
  ORG_KNOWLEDGE_MODEL=o1
  ORG_KNOWLEDGE_URL=https://llm-proxy-web.ai.openeng.netapp.com

  # ──────────── App settings ───────────────────────────────────────
  PORT=5001
  SECRET_KEY=<random-string-for-flask-sessions>
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Package requirements
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = [
    # package-name          pip-install-name           min version (None = any)
    ("flask",               "flask>=3.0",               "3.0"),
    ("jira",                "jira>=3.8",                "3.8"),
    ("openai",              "openai>=1.0",              "1.0"),
    ("httpx",               "httpx>=0.24",              "0.24"),
    ("openpyxl",            "openpyxl>=3.1",            "3.1"),
    ("yaml",                "PyYAML>=6.0",              "6.0"),
    ("anthropic",           "anthropic>=0.18",          "0.18"),
    ("google.generativeai", "google-generativeai>=0.4", "0.4"),
    ("requests",            "requests>=2.28",           "2.28"),
]

# ---------------------------------------------------------------------------
# Env vars: (name, required, description)
# ---------------------------------------------------------------------------

ENV_VARS = [
    # name                  required  description
    ("JIRA_TOKEN",          True,     "Jira Personal Access Token"),
    ("JIRA_SERVER",         False,    "Jira server URL (default: https://jira.ngage.netapp.com)"),
    ("NETAPP_LLM_KEY",      False,    "NetApp internal LLM proxy key  (needed for netapp provider)"),
    ("OPENAI_API_KEY",      False,    "OpenAI API key                 (needed for openai provider)"),
    ("ANTHROPIC_API_KEY",   False,    "Anthropic API key              (needed for anthropic provider)"),
    ("GOOGLE_API_KEY",      False,    "Google Gemini API key          (needed for gemini provider)"),
    ("ORG_KNOWLEDGE_KEY",   False,    "Org knowledge proxy key        (optional)"),
    ("ORG_KNOWLEDGE_MODEL", False,    "Org knowledge proxy model      (default: o1)"),
    ("ORG_KNOWLEDGE_URL",   False,    "Org knowledge proxy base URL   (optional)"),
    ("LLM_PROVIDER",        False,    "Default LLM provider           (default: mock)"),
    ("LLM_MODEL",           False,    "Default LLM model              (uses provider default)"),
    ("PORT",                False,    "Flask port                     (default: 5001)"),
    ("SECRET_KEY",          False,    "Flask session secret key"),
]

# ---------------------------------------------------------------------------
# Colours (disabled on Windows unless ANSI is enabled)
# ---------------------------------------------------------------------------

_WIN = platform.system() == "Windows"


def _c(code: str, text: str) -> str:
    if _WIN:
        return text
    return f"\033[{code}m{text}\033[0m"


OK   = _c("32", "✓")
WARN = _c("33", "⚠")
ERR  = _c("31", "✗")
INFO = _c("36", "ℹ")
BOLD = lambda s: _c("1", s)   # noqa: E731


def _header(title: str) -> None:
    print(f"\n{_c('1;34', '=' * 60)}")
    print(f"{_c('1;34', f'  {title}')}")
    print(f"{_c('1;34', '=' * 60)}")


# ---------------------------------------------------------------------------
# Step 1: Python version
# ---------------------------------------------------------------------------

def check_python() -> None:
    _header("Python version check")
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if v < (3, 10):
        print(f"{ERR}  Python {ver} is too old. BugBuddy requires Python 3.10+.")
        print(f"     Current executable: {sys.executable}")
        sys.exit(1)
    print(f"{OK}  Python {ver}  ({sys.executable})")


# ---------------------------------------------------------------------------
# Step 2: Install / upgrade packages
# ---------------------------------------------------------------------------

def install_packages() -> None:
    _header("Installing / updating packages")
    missing: list[str] = []
    outdated: list[str] = []

    for import_name, pip_spec, min_ver in REQUIRED_PACKAGES:
        try:
            mod = __import__(import_name.split(".")[0])
            ver = getattr(mod, "__version__", None) or getattr(mod, "VERSION", None)
            if ver and min_ver:
                from packaging.version import Version  # type: ignore
                try:
                    if Version(str(ver)) < Version(min_ver):
                        outdated.append(pip_spec)
                        print(f"{WARN}  {import_name} {ver} < {min_ver} — will upgrade")
                    else:
                        print(f"{OK}  {import_name} {ver}")
                except Exception:
                    print(f"{OK}  {import_name} (version unverified)")
            else:
                print(f"{OK}  {import_name}")
        except ImportError:
            missing.append(pip_spec)
            print(f"{WARN}  {import_name} — NOT FOUND, will install")

    to_install = missing + outdated
    if not to_install:
        print(f"\n{OK}  All packages are already up to date.")
        return

    print(f"\n{INFO}  Running: pip install --upgrade {' '.join(to_install)}")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + to_install
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n{ERR}  pip install failed. Try running manually:\n")
        print(f"     pip install --upgrade {' '.join(to_install)}\n")
        sys.exit(1)
    print(f"\n{OK}  All packages installed successfully.")


# ---------------------------------------------------------------------------
# Step 3: .env file
# ---------------------------------------------------------------------------

ENV_FILE      = Path(__file__).parent / ".env"
ENV_TEMPLATE  = Path(__file__).parent / ".env.template"


def setup_dotenv() -> None:
    _header(".env configuration file")

    if ENV_FILE.exists():
        print(f"{OK}  .env already exists — loading it.")
        _load_dotenv(ENV_FILE)
        return

    if ENV_TEMPLATE.exists():
        import shutil
        shutil.copy(ENV_TEMPLATE, ENV_FILE)
        print(f"{OK}  Created .env from .env.template")
        print(f"{WARN}  ACTION REQUIRED: Edit .env and fill in your credentials:")
        print(f"       {ENV_FILE}")
        _load_dotenv(ENV_FILE)
    else:
        print(f"{WARN}  No .env.template found. Creating a minimal .env")
        _write_minimal_dotenv()


def _load_dotenv(path: Path) -> None:
    """Simple dotenv loader — sets os.environ for variables not already set."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and key not in os.environ:
                os.environ[key] = val


def _write_minimal_dotenv() -> None:
    content = (
        "# BugBuddy environment — fill in your values before running the app\n"
        "# See setup_env.py docstring for full configuration reference\n"
        "\n"
        "# ────────── Jira ───────────────────────────────────────────────\n"
        "JIRA_SERVER=https://jira.ngage.netapp.com\n"
        "JIRA_TOKEN=\n"
        "\n"
        "# ────────── LLM provider ────────────────────────────────────\n"
        "# Options: netapp | openai | anthropic | gemini | mock\n"
        "LLM_PROVIDER=netapp\n"
        "LLM_MODEL=gpt-4.1\n"
        "NETAPP_LLM_KEY=\n"
        "\n"
        "# Uncomment ONE of the alternatives below instead:\n"
        "# LLM_PROVIDER=openai\n"
        "# LLM_MODEL=gpt-4o\n"
        "# OPENAI_API_KEY=\n"
        "#\n"
        "# LLM_PROVIDER=anthropic\n"
        "# LLM_MODEL=claude-3-5-sonnet-20241022\n"
        "# ANTHROPIC_API_KEY=\n"
        "#\n"
        "# LLM_PROVIDER=gemini\n"
        "# LLM_MODEL=gemini-1.5-pro\n"
        "# GOOGLE_API_KEY=\n"
        "\n"
        "# ────────── Org Knowledge proxy (optional) ──────────────\n"
        "ORG_KNOWLEDGE_KEY=\n"
        "ORG_KNOWLEDGE_MODEL=o1\n"
        "ORG_KNOWLEDGE_URL=https://llm-proxy-web.ai.openeng.netapp.com\n"
        "\n"
        "# ────────── App settings ──────────────────────────────────\n"
        "PORT=5001\n"
        "SECRET_KEY=bugbuddy-dev-secret-change-in-prod\n"
    )
    ENV_FILE.write_text(content, encoding="utf-8")
    print(f"{WARN}  .env written to {ENV_FILE}")
    print(f"{WARN}  ACTION REQUIRED: Edit .env and fill in your credentials.")


# ---------------------------------------------------------------------------
# Step 4: Validate env vars
# ---------------------------------------------------------------------------

def validate_env() -> None:
    _header("Environment variable validation")
    any_required_missing = False

    for name, required, description in ENV_VARS:
        val = os.environ.get(name, "")
        if val:
            # Never print the actual secret — just show it is set
            display = f"{'*' * min(len(val), 8)}…" if "KEY" in name or "TOKEN" in name or "SECRET" in name else val
            print(f"{OK}  {name:<28} {display}")
        elif required:
            print(f"{ERR}  {name:<28} NOT SET  ← {description}")
            any_required_missing = True
        else:
            print(f"{WARN}  {name:<28} not set  ({description})")

    # At least one LLM key should be set (warn only)
    llm_keys = ["NETAPP_LLM_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    if not any(os.environ.get(k) for k in llm_keys):
        print(f"\n{WARN}  No LLM provider key is set.")
        print(f"     The tool will run in MOCK mode (no real LLM analysis).")
        print(f"     Set NETAPP_LLM_KEY for the NetApp internal proxy.")

    if any_required_missing:
        print(f"\n{ERR}  One or more REQUIRED variables are missing.")
        print(f"     Edit .env or export them in your shell before starting the app.")
    else:
        print(f"\n{OK}  All required variables are set.")


# ---------------------------------------------------------------------------
# Step 5: Connectivity smoke test
# ---------------------------------------------------------------------------

def smoke_test() -> None:
    _header("Connectivity smoke test")
    try:
        import requests as req
        jira_url = os.environ.get("JIRA_SERVER", "https://jira.ngage.netapp.com")
        token    = os.environ.get("JIRA_TOKEN", "")
        if not token:
            print(f"{WARN}  Skipping Jira test — JIRA_TOKEN not set.")
            return
        print(f"{INFO}  Testing connection to {jira_url} …")
        resp = req.get(
            f"{jira_url}/rest/api/2/myself",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            verify=False,  # corp self-signed cert
        )
        if resp.status_code == 200:
            user = resp.json().get("displayName", resp.json().get("name", "?"))
            print(f"{OK}  Jira connected — logged in as: {BOLD(user)}")
        else:
            print(f"{WARN}  Jira returned HTTP {resp.status_code}. Check JIRA_TOKEN.")
    except Exception as exc:
        print(f"{WARN}  Jira connectivity test failed: {exc}")
        print(f"     This may be normal if you are off VPN.")


# ---------------------------------------------------------------------------
# Step 6: Print start instructions
# ---------------------------------------------------------------------------

def print_run_instructions() -> None:
    _header("Ready to run")
    port = os.environ.get("PORT", "5001")
    provider = os.environ.get("LLM_PROVIDER", "netapp")
    print(f"""
  Start the web app:
    {BOLD(f'python app.py')}

  Then open:  {BOLD(f'http://localhost:{port}')}

  Or run a single Jira via CLI:
    {BOLD(f'python test_llm_agent.py CFSHELF-5078 --provider {provider}')}

  To re-run this setup at any time:
    {BOLD('python setup_env.py')}
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="BugBuddy environment setup")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--install",  action="store_true", help="Install/upgrade packages only")
    group.add_argument("--validate", "--check", action="store_true",
                       help="Validate config only (no pip install)")
    args = parser.parse_args()

    check_python()

    if args.validate:
        setup_dotenv()
        validate_env()
        return

    if args.install:
        install_packages()
        return

    # Default: full setup
    install_packages()
    setup_dotenv()
    validate_env()
    smoke_test()
    print_run_instructions()


if __name__ == "__main__":
    main()

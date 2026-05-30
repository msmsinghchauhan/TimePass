#!/usr/bin/env bash
# =============================================================================
# setup.sh — BugBuddy setup script for macOS and Linux
# =============================================================================
# Usage:
#   chmod +x setup.sh && ./setup.sh          # full setup
#   ./setup.sh --install                     # pip install only
#   ./setup.sh --validate                    # validate config only
#   ./setup.sh --run                         # start the app (after setup)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET}  $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
err()  { echo -e "${RED}✗${RESET}  $*"; }
info() { echo -e "${CYAN}ℹ${RESET}  $*"; }
hdr()  { echo -e "\n${BOLD}${CYAN}============================================================${RESET}"; \
         echo -e "${BOLD}${CYAN}  $*${RESET}"; \
         echo -e "${BOLD}${CYAN}============================================================${RESET}"; }

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
MODE="full"
case "${1:-}" in
  --install)  MODE="install"  ;;
  --validate) MODE="validate" ;;
  --run)      MODE="run"      ;;
esac

# Resolve script directory (works even when called from another dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# 1. Python check
# ---------------------------------------------------------------------------
check_python() {
  hdr "Python version check"

  # Prefer python3, fall back to python
  PYTHON=""
  for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
      VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      MAJOR=$(echo "$VER" | cut -d. -f1)
      MINOR=$(echo "$VER" | cut -d. -f2)
      if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
        PYTHON="$cmd"
        ok "Python $VER  ($(command -v $cmd))"
        break
      else
        warn "Found Python $VER — too old (need 3.10+), trying next…"
      fi
    fi
  done

  if [ -z "$PYTHON" ]; then
    err "Python 3.10+ not found."
    echo "  macOS:  brew install python@3.12"
    echo "  Linux:  sudo apt install python3.12   OR   sudo dnf install python3.12"
    exit 1
  fi

  export PYTHON
}

# ---------------------------------------------------------------------------
# 2. pip packages
# ---------------------------------------------------------------------------
install_packages() {
  hdr "Installing / updating Python packages"

  PACKAGES=(
    "flask>=3.0"
    "jira>=3.8"
    "openai>=1.0"
    "httpx>=0.24"
    "openpyxl>=3.1"
    "PyYAML>=6.0"
    "anthropic>=0.18"
    "google-generativeai>=0.4"
    "requests>=2.28"
    "packaging"
  )

  info "Running: $PYTHON -m pip install --upgrade ${PACKAGES[*]}"
  "$PYTHON" -m pip install --upgrade --quiet "${PACKAGES[@]}"
  ok "All packages installed / up to date."
}

# ---------------------------------------------------------------------------
# 3. .env setup
# ---------------------------------------------------------------------------
setup_dotenv() {
  hdr ".env configuration"

  if [ -f ".env" ]; then
    ok ".env already exists."
  elif [ -f ".env.template" ]; then
    cp .env.template .env
    ok "Created .env from .env.template"
    echo ""
    warn "ACTION REQUIRED: Edit .env and fill in your credentials."
    warn "  File: $SCRIPT_DIR/.env"
    echo ""
    echo "  Minimum required:"
    echo "    JIRA_TOKEN=<your-jira-personal-access-token>"
    echo "    NETAPP_LLM_KEY=<your-netapp-llm-proxy-key>"
    echo ""
    read -rp "  Open .env in your default editor now? [y/N] " OPEN_NOW
    if [[ "${OPEN_NOW,,}" == "y" ]]; then
      "${EDITOR:-nano}" .env
    fi
  else
    warn ".env.template not found — creating minimal .env"
    cat > .env <<'EOF'
# BugBuddy environment — fill in your values
JIRA_TOKEN=
NETAPP_LLM_KEY=
LLM_PROVIDER=netapp
PORT=5001
SECRET_KEY=bugbuddy-dev-secret-change-in-prod
EOF
    warn "Edit .env before starting the app."
  fi

  # Load .env into current shell session (for the smoke test below)
  set -a
  # shellcheck disable=SC1091
  source .env 2>/dev/null || true
  set +a
}

# ---------------------------------------------------------------------------
# 4. Validate env
# ---------------------------------------------------------------------------
validate_env() {
  hdr "Environment variable validation"
  # Load .env if present
  if [ -f ".env" ]; then
    set -a; source .env 2>/dev/null || true; set +a
  fi

  FAIL=0

  check_var() {
    local name="$1" required="$2" desc="$3"
    local val="${!name:-}"
    if [ -n "$val" ]; then
      # Mask secrets
      if [[ "$name" == *"KEY"* || "$name" == *"TOKEN"* || "$name" == *"SECRET"* ]]; then
        display="$(echo "$val" | head -c 6)…"
      else
        display="$val"
      fi
      printf "${GREEN}✓${RESET}  %-28s %s\n" "$name" "$display"
    elif [ "$required" = "true" ]; then
      printf "${RED}✗${RESET}  %-28s NOT SET  ← %s\n" "$name" "$desc"
      FAIL=1
    else
      printf "${YELLOW}⚠${RESET}  %-28s not set  (%s)\n" "$name" "$desc"
    fi
  }

  check_var "JIRA_TOKEN"          true  "Jira Personal Access Token (required)"
  check_var "JIRA_SERVER"         false "Jira server URL"
  check_var "NETAPP_LLM_KEY"      false "NetApp LLM proxy key"
  check_var "OPENAI_API_KEY"      false "OpenAI API key"
  check_var "ANTHROPIC_API_KEY"   false "Anthropic API key"
  check_var "GOOGLE_API_KEY"      false "Google Gemini API key"
  check_var "ORG_KNOWLEDGE_KEY"   false "Org knowledge proxy key"
  check_var "ORG_KNOWLEDGE_MODEL" false "Org knowledge proxy model"
  check_var "LLM_PROVIDER"        false "Default LLM provider"
  check_var "LLM_MODEL"           false "Default LLM model"
  check_var "PORT"                false "Flask port"
  check_var "SECRET_KEY"          false "Flask session secret"

  # Warn if no LLM key set
  if [ -z "${NETAPP_LLM_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ] && \
     [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
    echo ""
    warn "No LLM provider key is set — tool will run in MOCK mode."
    warn "Set NETAPP_LLM_KEY in .env for the NetApp internal proxy."
  fi

  if [ "$FAIL" -eq 1 ]; then
    echo ""
    err "Required variables are missing. Edit .env before starting the app."
  else
    echo ""
    ok "All required variables are set."
  fi
}

# ---------------------------------------------------------------------------
# 5. Connectivity smoke test
# ---------------------------------------------------------------------------
smoke_test() {
  hdr "Connectivity smoke test"
  if [ -f ".env" ]; then
    set -a; source .env 2>/dev/null || true; set +a
  fi

  JIRA_URL="${JIRA_SERVER:-https://jira.ngage.netapp.com}"
  TOKEN="${JIRA_TOKEN:-}"

  if [ -z "$TOKEN" ]; then
    warn "Skipping Jira test — JIRA_TOKEN not set."
    return
  fi

  info "Testing connection to $JIRA_URL …"
  HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "${JIRA_URL}/rest/api/2/myself" --max-time 10 2>/dev/null || echo "000")

  if [ "$HTTP_CODE" = "200" ]; then
    ok "Jira is reachable and token is valid (HTTP 200)."
  elif [ "$HTTP_CODE" = "401" ]; then
    warn "Jira returned HTTP 401 — token may be invalid or expired."
  elif [ "$HTTP_CODE" = "000" ]; then
    warn "Could not reach $JIRA_URL — check VPN / network."
  else
    warn "Jira returned HTTP $HTTP_CODE."
  fi
}

# ---------------------------------------------------------------------------
# 6. Print run instructions
# ---------------------------------------------------------------------------
print_run_instructions() {
  if [ -f ".env" ]; then
    set -a; source .env 2>/dev/null || true; set +a
  fi
  PORT_VAL="${PORT:-5001}"
  PROVIDER_VAL="${LLM_PROVIDER:-netapp}"

  hdr "Setup complete — ready to run"
  echo ""
  echo -e "  Start the web app:"
  echo -e "    ${BOLD}python app.py${RESET}"
  echo ""
  echo -e "  Then open:  ${BOLD}http://localhost:${PORT_VAL}${RESET}"
  echo ""
  echo -e "  CLI analysis:"
  echo -e "    ${BOLD}python test_llm_agent.py CFSHELF-5078 --provider ${PROVIDER_VAL}${RESET}"
  echo ""
  echo -e "  To re-run this setup:"
  echo -e "    ${BOLD}./setup.sh${RESET}"
  echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
case "$MODE" in
  install)
    check_python
    install_packages
    ;;
  validate)
    check_python
    validate_env
    smoke_test
    ;;
  run)
    if [ -f ".env" ]; then set -a; source .env 2>/dev/null || true; set +a; fi
    check_python
    info "Starting BugBuddy…"
    "$PYTHON" app.py
    ;;
  full|*)
    check_python
    install_packages
    setup_dotenv
    validate_env
    smoke_test
    print_run_instructions
    ;;
esac

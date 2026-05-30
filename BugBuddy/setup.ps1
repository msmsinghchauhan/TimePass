# =============================================================================
# setup.ps1 — BugBuddy setup script for Windows (PowerShell 5.1+ / 7+)
# =============================================================================
# Usage (run in PowerShell as normal user):
#   .\setup.ps1              # full setup
#   .\setup.ps1 -Install     # pip install only
#   .\setup.ps1 -Validate    # validate config only
#   .\setup.ps1 -Run         # start the app
#
# If you get "execution of scripts is disabled", run once:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# =============================================================================

param(
    [switch]$Install,
    [switch]$Validate,
    [switch]$Run
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
function ok   { param($msg) Write-Host "✓  $msg" -ForegroundColor Green }
function warn { param($msg) Write-Host "⚠  $msg" -ForegroundColor Yellow }
function err  { param($msg) Write-Host "✗  $msg" -ForegroundColor Red }
function info { param($msg) Write-Host "ℹ  $msg" -ForegroundColor Cyan }
function hdr  {
    param($title)
    $line = "=" * 60
    Write-Host "`n$line" -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "$line" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# 1. Python check
# ---------------------------------------------------------------------------
function Check-Python {
    hdr "Python version check"

    $pythonCmds = @("python", "python3", "py")
    $script:PYTHON = $null

    foreach ($cmd in $pythonCmds) {
        try {
            $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $parts = $ver.Split(".")
                if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 10) {
                    ok "Python $ver  ($(Get-Command $cmd | Select-Object -ExpandProperty Source))"
                    $script:PYTHON = $cmd
                    return
                } else {
                    warn "Found Python $ver — too old (need 3.10+), trying next…"
                }
            }
        } catch { }
    }

    err "Python 3.10+ not found."
    Write-Host "  Download from: https://www.python.org/downloads/"
    Write-Host "  Or via winget: winget install Python.Python.3.12"
    exit 1
}

# ---------------------------------------------------------------------------
# 2. pip packages
# ---------------------------------------------------------------------------
function Install-Packages {
    hdr "Installing / updating Python packages"

    $packages = @(
        "flask>=3.0",
        "jira>=3.8",
        "openai>=1.0",
        "httpx>=0.24",
        "openpyxl>=3.1",
        "PyYAML>=6.0",
        "anthropic>=0.18",
        "google-generativeai>=0.4",
        "requests>=2.28",
        "packaging"
    )

    info "Running: $script:PYTHON -m pip install --upgrade $($packages -join ' ')"
    & $script:PYTHON -m pip install --upgrade --quiet @packages
    if ($LASTEXITCODE -ne 0) {
        err "pip install failed. Try running manually:"
        Write-Host "  $script:PYTHON -m pip install --upgrade $($packages -join ' ')"
        exit 1
    }
    ok "All packages installed / up to date."
}

# ---------------------------------------------------------------------------
# 3. .env setup
# ---------------------------------------------------------------------------
function Setup-DotEnv {
    hdr ".env configuration"

    if (Test-Path ".env") {
        ok ".env already exists."
        Load-DotEnv
        return
    }

    if (Test-Path ".env.template") {
        Copy-Item ".env.template" ".env"
        ok "Created .env from .env.template"
        Write-Host ""
        warn "ACTION REQUIRED: Edit .env and fill in your credentials."
        warn "  File: $ScriptDir\.env"
        Write-Host ""
        Write-Host "  Minimum required:"
        Write-Host "    JIRA_TOKEN=<your-jira-personal-access-token>"
        Write-Host "    NETAPP_LLM_KEY=<your-netapp-llm-proxy-key>"
        Write-Host ""
        $openNow = Read-Host "  Open .env in Notepad now? [y/N]"
        if ($openNow -eq "y" -or $openNow -eq "Y") {
            Start-Process notepad.exe ".env" -Wait
        }
    } else {
        warn ".env.template not found — creating minimal .env"
        @"
# BugBuddy environment — fill in your values
JIRA_TOKEN=
NETAPP_LLM_KEY=
LLM_PROVIDER=netapp
PORT=5001
SECRET_KEY=bugbuddy-dev-secret-change-in-prod
"@ | Out-File -FilePath ".env" -Encoding UTF8
        warn "Edit .env before starting the app."
    }
    Load-DotEnv
}

function Load-DotEnv {
    if (-not (Test-Path ".env")) { return }
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -match "^#" -or $line -eq "") { return }
        if ($line -match "^([^=]+)=(.*)$") {
            $key = $Matches[1].Trim()
            $val = $Matches[2].Trim()
            if (-not [System.Environment]::GetEnvironmentVariable($key)) {
                [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
            }
        }
    }
}

# ---------------------------------------------------------------------------
# 4. Validate env vars
# ---------------------------------------------------------------------------
function Validate-Env {
    hdr "Environment variable validation"
    Load-DotEnv

    $fail = $false

    function Check-Var {
        param($name, [bool]$required, $desc)
        $val = [System.Environment]::GetEnvironmentVariable($name)
        if ($val) {
            $display = if ($name -match "KEY|TOKEN|SECRET") { $val.Substring(0, [Math]::Min(6, $val.Length)) + "…" } else { $val }
            Write-Host ("✓  {0,-28} {1}" -f $name, $display) -ForegroundColor Green
        } elseif ($required) {
            Write-Host ("✗  {0,-28} NOT SET  ← {1}" -f $name, $desc) -ForegroundColor Red
            $script:fail = $true
        } else {
            Write-Host ("⚠  {0,-28} not set  ({1})" -f $name, $desc) -ForegroundColor Yellow
        }
    }

    Check-Var "JIRA_TOKEN"          $true  "Jira Personal Access Token (required)"
    Check-Var "JIRA_SERVER"         $false "Jira server URL"
    Check-Var "NETAPP_LLM_KEY"      $false "NetApp LLM proxy key"
    Check-Var "OPENAI_API_KEY"      $false "OpenAI API key"
    Check-Var "ANTHROPIC_API_KEY"   $false "Anthropic API key"
    Check-Var "GOOGLE_API_KEY"      $false "Google Gemini API key"
    Check-Var "ORG_KNOWLEDGE_KEY"   $false "Org knowledge proxy key"
    Check-Var "ORG_KNOWLEDGE_MODEL" $false "Org knowledge proxy model"
    Check-Var "LLM_PROVIDER"        $false "Default LLM provider"
    Check-Var "LLM_MODEL"           $false "Default LLM model"
    Check-Var "PORT"                $false "Flask port"
    Check-Var "SECRET_KEY"          $false "Flask session secret"

    $llmKeys = @("NETAPP_LLM_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY","GOOGLE_API_KEY")
    $hasLlmKey = $llmKeys | Where-Object { [System.Environment]::GetEnvironmentVariable($_) }
    if (-not $hasLlmKey) {
        Write-Host ""
        warn "No LLM provider key is set — tool will run in MOCK mode."
        warn "Set NETAPP_LLM_KEY in .env for the NetApp internal proxy."
    }

    Write-Host ""
    if ($fail) {
        err "Required variables are missing. Edit .env before starting the app."
    } else {
        ok "All required variables are set."
    }
}

# ---------------------------------------------------------------------------
# 5. Connectivity smoke test
# ---------------------------------------------------------------------------
function Smoke-Test {
    hdr "Connectivity smoke test"
    Load-DotEnv

    $jiraUrl = [System.Environment]::GetEnvironmentVariable("JIRA_SERVER")
    if (-not $jiraUrl) { $jiraUrl = "https://jira.ngage.netapp.com" }
    $token = [System.Environment]::GetEnvironmentVariable("JIRA_TOKEN")

    if (-not $token) {
        warn "Skipping Jira test — JIRA_TOKEN not set."
        return
    }

    info "Testing connection to $jiraUrl …"
    try {
        # Disable SSL validation for corporate self-signed certs
        add-type @"
using System.Net;using System.Security.Cryptography.X509Certificates;
public class TrustAll : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int err) { return true; }
}
"@
        [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAll
        [System.Net.ServicePointManager]::SecurityProtocol  = [System.Net.SecurityProtocolType]::Tls12

        $resp = Invoke-WebRequest -Uri "$jiraUrl/rest/api/2/myself" `
            -Headers @{Authorization="Bearer $token"} `
            -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $user = ($resp.Content | ConvertFrom-Json).displayName
            ok "Jira connected — logged in as: $user"
        }
    } catch {
        $code = $_.Exception.Response?.StatusCode?.value__
        if ($code -eq 401) {
            warn "Jira returned HTTP 401 — token may be invalid or expired."
        } else {
            warn "Jira connectivity test failed: $($_.Exception.Message)"
            warn "This may be normal if you are off VPN."
        }
    }
}

# ---------------------------------------------------------------------------
# 6. Print run instructions
# ---------------------------------------------------------------------------
function Print-RunInstructions {
    Load-DotEnv
    $port     = [System.Environment]::GetEnvironmentVariable("PORT");     if (-not $port)     { $port = "5001" }
    $provider = [System.Environment]::GetEnvironmentVariable("LLM_PROVIDER"); if (-not $provider) { $provider = "netapp" }

    hdr "Setup complete — ready to run"
    Write-Host ""
    Write-Host "  Start the web app:"
    Write-Host "    python app.py" -ForegroundColor White
    Write-Host ""
    Write-Host "  Then open:  http://localhost:$port" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  CLI analysis:"
    Write-Host "    python test_llm_agent.py CFSHELF-5078 --provider $provider" -ForegroundColor White
    Write-Host ""
    Write-Host "  To re-run this setup:"
    Write-Host "    .\setup.ps1" -ForegroundColor White
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if ($Run) {
    Load-DotEnv
    Check-Python
    info "Starting BugBuddy…"
    & $script:PYTHON app.py
    exit
}

if ($Install) {
    Check-Python
    Install-Packages
    exit
}

if ($Validate) {
    Check-Python
    Validate-Env
    Smoke-Test
    exit
}

# Full setup
Check-Python
Install-Packages
Setup-DotEnv
Validate-Env
Smoke-Test
Print-RunInstructions

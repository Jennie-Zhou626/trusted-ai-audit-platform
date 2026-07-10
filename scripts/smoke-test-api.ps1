$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$pythonCandidates = @(
    "python",
    "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
)

$python = $null
foreach ($candidate in $pythonCandidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
        $python = $command.Source
        break
    }
}

if (-not $python) {
    throw "未找到 Python。请先安装 Python，或确认 Codex 运行时已安装。"
}

Set-Location $root
@'
import requests

API = "http://127.0.0.1:8000/api"

requests.get(f"{API}/health", timeout=5).raise_for_status()
result = requests.post(f"{API}/demo/seed-showcase", data={"reset": "true"}, timeout=30).json()
audits = requests.get(f"{API}/audits", timeout=5).json()

if result["normal_audit"] != "passed":
    raise SystemExit(f"normal audit failed: {result}")
if result["tampered_audit"] != "failed":
    raise SystemExit(f"tamper audit did not fail: {result}")
if len(audits) != 2:
    raise SystemExit(f"expected 2 audits, got {len(audits)}")

print(result)
'@ | & $python -

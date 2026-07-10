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
& $python "$root/scripts/seed_sample_project.py"

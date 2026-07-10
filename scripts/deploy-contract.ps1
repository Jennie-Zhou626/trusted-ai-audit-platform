$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$nodeBin = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if (Test-Path $nodeBin) {
    $env:PATH = "$nodeBin;$env:PATH"
}

Set-Location "$root/contracts"
$npm = (Get-Command "npm.cmd" -ErrorAction SilentlyContinue).Source
if (-not $npm) {
    $npm = (Get-Command "npm" -ErrorAction SilentlyContinue).Source
}
if (-not $npm) {
    throw "未找到 npm。请先安装 Node.js/npm。"
}
& $npm install
& $npm run compile
& $npm run deploy

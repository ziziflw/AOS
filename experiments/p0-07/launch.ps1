param([ValidatePattern('^[A-Za-z0-9_-]{1,40}$')][string]$SessionName='desktop')
$ErrorActionPreference='Stop'
$experimentRoot=$PSScriptRoot
$program=Join-Path $experimentRoot 'host/target/debug/host-window.exe'
if(-not (Test-Path -LiteralPath $program)){throw '请先按 README 构建本轮宿主。'}
$sessionRoot=Join-Path $experimentRoot ('evidence/session-'+$SessionName)
New-Item -ItemType Directory -Force -Path $sessionRoot | Out-Null
# Normal mode: real window, no test crash command or WebView debug port.
& $program $experimentRoot $sessionRoot

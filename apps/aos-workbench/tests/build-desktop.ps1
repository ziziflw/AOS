param([switch]$Integrated)
# Build the existing trusted test window with this UI in an isolated crate.
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$original = (Resolve-Path (Join-Path $workspace '../../demo/studio/host')).Path
$assets = if ($Integrated) { "dist-integrated" } else { "dist" }
$entryFile = if ($Integrated) { "integration.html" } else { "index.html" }
if (!(Test-Path (Join-Path $workspace "$assets/$entryFile"))) { throw '请先运行 npm run build' }
$fixture = Join-Path $env:TEMP ('aos-react-ui-host-1108'+ $(if($Integrated){"-integrated"}))
New-Item -ItemType Directory -Force $fixture | Out-Null
foreach ($entry in @('src','capabilities','permissions','icons','Cargo.toml','Cargo.lock','build.rs','tauri.conf.json')) {
  Copy-Item -LiteralPath (Join-Path $original $entry) -Destination $fixture -Recurse -Force
}
$ui = New-Item -ItemType Directory -Force (Join-Path $fixture 'ui')
Copy-Item (Join-Path $workspace "$assets/*") -Destination $ui.FullName -Recurse -Force
if($Integrated){Copy-Item -LiteralPath (Join-Path $ui.FullName $entryFile) (Join-Path $ui.FullName "index.html") -Force}
$previousTarget = $env:CARGO_TARGET_DIR
Push-Location $fixture
try {
  $env:CARGO_TARGET_DIR = Join-Path $fixture 'target'
  cargo build --locked --offline --features window --bin host-window
  if ($LASTEXITCODE -ne 0) { throw 'Tauri test host build failed' }
  $destination = New-Item -ItemType Directory -Force (Join-Path $workspace '.desktop-preview')
  Copy-Item (Join-Path $env:CARGO_TARGET_DIR 'debug/host-window.exe') (Join-Path $destination.FullName $(if($Integrated){"AOS-Integrated.exe"}else{"AOS-UI.exe"})) -Force
} finally {
  $env:CARGO_TARGET_DIR = $previousTarget
  Pop-Location
}

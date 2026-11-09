param([string]$OutputRoot = "$PSScriptRoot\dist")
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$source = Join-Path $project 'experiments/p0-08'
$destination = Join-Path $OutputRoot ('AOS-Demo-win-x64-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $destination) { throw 'Output already exists' }
New-Item -ItemType Directory -Path $destination | Out-Null
function Copy-Tree($From, $To, $Excluded) {
    & robocopy $From $To /E /XD @Excluded /XF '*.pyc' /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "Copy failed: $From" }
}
foreach ($stage in 'p0-03','p0-04','p0-05','p0-06','p0-07','p0-08') {
    Copy-Tree (Join-Path $project "experiments/$stage") (Join-Path $destination "experiments/$stage") @('.venv','node_modules','target','evidence','workspace','__pycache__','.git','wheelhouse','source-archives','frontend')
}
Copy-Tree (Join-Path $project 'research') (Join-Path $destination 'research') @('__pycache__')
$runtime = Join-Path $destination 'experiments/p0-08/.venv'
$base = & "$source/.venv/Scripts/python.exe" -c 'import sys; print(sys.base_prefix)'
Copy-Tree $base $runtime @('site-packages','__pycache__','Scripts','include','libs','tcl')
Copy-Tree "$source/.venv/Lib/site-packages" "$runtime/Lib/site-packages" @('__pycache__')
New-Item -ItemType Directory -Path "$runtime/Scripts" -Force | Out-Null
Copy-Item "$base/python.exe" "$runtime/Scripts/python.exe"
Copy-Item "$base/*.dll" "$runtime/Scripts/"
@('../Lib','../DLLs','../Lib/site-packages','../Lib/site-packages/win32','../Lib/site-packages/win32/lib','../Lib/site-packages/pythonwin','../Lib/site-packages/pywin32_system32','import site') | Set-Content "$runtime/Scripts/python._pth" -Encoding ascii
Copy-Item "$runtime/Lib/site-packages/pywin32_system32/*.dll" "$runtime/Scripts/"
Add-Content "$runtime/Scripts/python._pth" '../..' -Encoding ascii
$binaryDirectory = Join-Path $destination 'experiments/p0-08/host/target/debug'
New-Item -ItemType Directory -Path "$destination/experiments/p0-08/evidence" -Force | Out-Null
New-Item -ItemType Directory -Path $binaryDirectory -Force | Out-Null
foreach ($binary in 'host-window.exe','host-probe.exe') {
    Copy-Item "$source/host/target/debug/$binary" $binaryDirectory
}
Copy-Item "$PSScriptRoot/Start-Demo.cmd" $destination
Copy-Item "$PSScriptRoot/README.md" $destination
$manifest = Get-ChildItem $destination -File -Recurse | ForEach-Object {
    [ordered]@{path=$_.FullName.Substring($destination.Length+1); sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash; bytes=$_.Length}
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content "$destination/manifest.json" -Encoding utf8
& "$runtime/Scripts/python.exe" -c 'import ssl,sqlite3,openai,anthropic,mcp,a2a,win32cred; print("Runtime imports OK")'
if ($LASTEXITCODE -ne 0) { throw 'Packaged runtime validation failed' }
Write-Output $destination

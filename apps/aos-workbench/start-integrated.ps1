param([switch]$PrepareOnly)
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'AOS-Demo'
$install=Join-Path $base 'p011'
$project=(Resolve-Path "$PSScriptRoot/../..").Path
$source=Join-Path $project 'dist/AOS-Demo-v0.1.3-win-x64/app'
if (!(Test-Path "$install/experiments/p0-08/executor.py")){
  $stage=Join-Path $base ('prepare-p011-'+[guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force $stage|Out-Null
  # Use the bundled private runtime, excluding development or previous session data.
  robocopy "$source/experiments" "$stage/experiments" /E /XJ /XD evidence workspace __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8){throw 'Private runtime copy failed'}
  Copy-Item -Recurse "$source/research" $stage
  $rt="$stage/experiments/p0-08"
  Copy-Item -Force "$project/demo/local_models.py" "$rt/local_models.py"
  $old="$base/v0.1.3/experiments/p0-08/workspace/local-models.json"
  if(Test-Path $old){
    $previous=Get-Content -LiteralPath $old -Raw -Encoding UTF8|ConvertFrom-Json
    $settings=@{}
    foreach($provider in @('LM Studio','Ollama')){
      $v=$previous.$provider
      if($v.url -match '^http://127\.0\.0\.1:[0-9]{1,5}/v1/?$' -and $v.model -is [string] -and $v.model.Length -le 256){
        $settings[$provider]=@{url=$v.url;model=$v.model}
      }
    }
    New-Item -ItemType Directory -Force "$rt/workspace"|Out-Null
    [IO.File]::WriteAllText("$rt/workspace/local-models.json",($settings|ConvertTo-Json))
  }
  try{[IO.Directory]::Move($stage,$install)}catch{if(!(Test-Path "$install/experiments/p0-08/executor.py")){throw}}
}
$root=Join-Path $install 'experiments/p0-08'
if(!$PrepareOnly){
  $exe=Join-Path $PSScriptRoot '.desktop-preview/AOS-Integrated.exe'
  Start-Process -FilePath $exe -ArgumentList ('"'+$root+'"'),('"'+(Join-Path $root 'evidence/p011-desktop')+'"')
}


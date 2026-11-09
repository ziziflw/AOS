$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../..").Path
$dst="$PSScriptRoot/.runtime"
if(!(Test-Path "$dst/experiments/p0-08/executor.py")){
  Copy-Item -Recurse "$project/dist/AOS-Demo-v0.1.3-win-x64/app" $dst
}
$rt="$dst/experiments/p0-08"
Copy-Item "$project/demo/local_models.py" "$rt/local_models.py" -Force
New-Item -Type Directory -Force "$rt/workspace"|Out-Null
@{'LM Studio'=@{url='http://127.0.0.1:1234/v1';model='google/gemma-4-e4b'}}|ConvertTo-Json|Set-Content "$rt/workspace/local-models.json" -Encoding utf8


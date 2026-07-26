$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$HuggingFace = Join-Path $Root '.venv\Scripts\hf.exe'
$ModelDir = Join-Path $Root 'resources\models\bamibert_vimedner'
$Revision = 'e508eedd34d124e05cf139cc565806c6d4fc5aad'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Missing uv. Install it from https://docs.astral.sh/uv/.'
}

if (-not (Test-Path -LiteralPath $Python)) {
    uv venv --python 3.12 (Join-Path $Root '.venv')
}
uv pip install --link-mode copy --python $Python `
    -r (Join-Path $Root 'requirements-teacher.txt')

& $HuggingFace download cbc-528a/BamiBERT-ViMedNER `
    --revision $Revision `
    --local-dir $ModelDir

Write-Output "Teacher model ready: $ModelDir"

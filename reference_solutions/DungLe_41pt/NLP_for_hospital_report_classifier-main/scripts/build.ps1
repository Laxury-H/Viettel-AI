param(
    [ValidateSet('production', 'v23')]
    [string]$Profile = 'production',
    [switch]$RefreshTeacher
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$InputDir = Join-Path $Root 'input'
$TeacherCache = Join-Path $Root '.work\bamibert_spans.json'
$ModelDir = Join-Path $Root 'resources\models\bamibert_vimedner'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Revision = 'e508eedd34d124e05cf139cc565806c6d4fc5aad'
$env:PYTHONPATH = Join-Path $Root 'src'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path -LiteralPath (Join-Path $InputDir '1.txt'))) {
    throw 'Missing input/1.txt.'
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Missing .venv. Run .\scripts\setup.ps1 first.'
}
if ($RefreshTeacher -or -not (Test-Path -LiteralPath $TeacherCache)) {
    if (-not (Test-Path -LiteralPath (Join-Path $ModelDir 'model.safetensors'))) {
        throw 'Missing BamiBERT weights. Run .\scripts\setup.ps1 first.'
    }
    & $Python (Join-Path $Root 'scripts\predict_bamibert.py') `
        --input $InputDir `
        --model $ModelDir `
        --output $TeacherCache `
        --minimum 0.50 `
        --revision $Revision
}

switch ($Profile) {
    'production' {
        $WorkDir = Join-Path $Root '.work\production'
        $ZipPath = Join-Path $Root 'submission\output.zip'
        $ReportPath = Join-Path $Root 'reports\production.json'
    }
    'v23' {
        $WorkDir = Join-Path $Root '.work\v23'
        $ZipPath = Join-Path $Root 'submission\candidate_v23_symptom-boundary-trim.zip'
        $ReportPath = Join-Path $Root 'reports\candidate_v23_symptom-boundary-trim.json'
    }
}
[IO.Directory]::CreateDirectory($WorkDir) | Out-Null

& $Python -m clinical_mentions.pipeline `
    --input $InputDir `
    --output $WorkDir `
    --zip $ZipPath `
    --teacher-cache $TeacherCache `
    --profile $Profile `
    --report $ReportPath

& $Python (Join-Path $Root 'scripts\validate_submission.py') `
    $ZipPath `
    --input $InputDir

$Hash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "$ZipPath SHA-256: $Hash"

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$InputDir = Join-Path $Root 'input'
$FirstCache = Join-Path $Root '.work\bamibert_spans.json'
$SecondCache = Join-Path $Root '.work\vipubmed_spans_seed42.json'
$env:PYTHONPATH = Join-Path $Root 'src'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path -LiteralPath (Join-Path $InputDir '1.txt'))) {
    throw 'Missing input/1.txt.'
}
foreach ($Cache in @($FirstCache, $SecondCache)) {
    if (-not (Test-Path -LiteralPath $Cache)) {
        throw "Missing teacher inference cache: $Cache"
    }
}

foreach ($Profile in @(
    'additive-94',
    'boundary-94',
    'boundary-94-single',
    'boundary-94-single-causal',
    'boundary-95',
    'boundary-95-single',
    'boundary-97',
    'boundary-97-single',
    'boundary-98',
    'boundary-98-single',
    'boundary-98-single-stable',
    'boundary-9825',
    'boundary-9825-single',
    'boundary-985',
    'boundary-985-single',
    'boundary-9875'
)) {
    $WorkDir = Join-Path $Root ".work\v17-$Profile"
    $ZipPath = Join-Path $Root "submission\candidate_v17_$Profile.zip"
    $ReportPath = Join-Path $Root "reports\final\candidate_v17_$Profile.json"
    [IO.Directory]::CreateDirectory($WorkDir) | Out-Null

    python -m clinical_mentions.turn2_v17 `
        --input $InputDir `
        --output $WorkDir `
        --zip $ZipPath `
        --first-cache $FirstCache `
        --second-cache $SecondCache `
        --profile $Profile `
        --report $ReportPath

    python (Join-Path $Root 'scripts\validate_submission.py') `
        $ZipPath `
        --input $InputDir

    $Hash = (
        Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    Write-Output "submission/candidate_v17_$Profile.zip SHA-256: $Hash"
}

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$InputDir = Join-Path $Root 'input'
$Baseline = Join-Path $Root 'submission\candidate_v18_v21-merge.zip'
$FirstCache = Join-Path $Root '.work\bamibert_spans.json'
$SecondCache = Join-Path $Root '.work\xlmr_spans_seed42.json'
$env:PYTHONPATH = Join-Path $Root 'src'
$env:PYTHONUTF8 = '1'

foreach ($Path in @(
    (Join-Path $InputDir '1.txt'),
    $Baseline,
    $FirstCache,
    $SecondCache
)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required input: $Path"
    }
}

foreach ($Profile in @(
    'xlmr-additive-90',
    'xlmr-additive-85',
    'xlmr-additive-80',
    'xlmr-safe-94',
    'xlmr-safe-93',
    'xlmr-safe-91'
)) {
    $WorkDir = Join-Path $Root ".work\candidate_v19_$Profile"
    $ZipPath = Join-Path $Root "submission\candidate_v19_$Profile.zip"
    $ReportPath = Join-Path $Root "reports\final\candidate_v19_$Profile.json"
    [IO.Directory]::CreateDirectory($WorkDir) | Out-Null

    python -m clinical_mentions.turn2_v19 `
        --input $InputDir `
        --baseline-zip $Baseline `
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
    Write-Output "submission/candidate_v19_$Profile.zip SHA-256: $Hash"
}

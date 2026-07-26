$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$InputDir = Join-Path $Root 'input'
$FirstCache = Join-Path $Root '.work\bamibert_spans.json'
$SecondCache = Join-Path $Root '.work\vipubmed_spans_seed42.json'
$env:PYTHONPATH = Join-Path $Root 'src'
$env:PYTHONUTF8 = '1'

foreach ($Path in @(
    (Join-Path $InputDir '1.txt'),
    $FirstCache,
    $SecondCache
)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required input: $Path"
    }
}

foreach ($Profile in @('v21-merge', 'v23-trim')) {
    $WorkDir = Join-Path $Root ".work\v18-$Profile"
    $ZipPath = Join-Path $Root "submission\candidate_v18_$Profile.zip"
    $ReportPath = Join-Path $Root "reports\final\candidate_v18_$Profile.json"
    [IO.Directory]::CreateDirectory($WorkDir) | Out-Null

    python -m clinical_mentions.turn2_v18 `
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
    Write-Output "submission/candidate_v18_$Profile.zip SHA-256: $Hash"
}

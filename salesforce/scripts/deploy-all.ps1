param(
    [string]$TargetOrg = "MY_SANDBOX_ALIAS",
    [string]$SourceDir = "force-app"
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SalesforceRoot = Split-Path -Parent $ScriptRoot

if (-not (Get-Command sf -ErrorAction SilentlyContinue)) {
    throw "Salesforce CLI ('sf') is not installed or not on PATH."
}

if (-not [System.IO.Path]::IsPathRooted($SourceDir)) {
    $SourceDir = Join-Path $SalesforceRoot $SourceDir
}

if (-not (Test-Path $SourceDir)) {
    throw "Source directory not found: $SourceDir"
}

Push-Location $SalesforceRoot
try {
    & sf project deploy start --source-dir $SourceDir --target-org $TargetOrg
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
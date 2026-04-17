param(
    [string]$TargetOrg = "MY_SANDBOX_ALIAS",
    [string]$ManifestPath = "manifest/package.xml"
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SalesforceRoot = Split-Path -Parent $ScriptRoot

if (-not (Get-Command sf -ErrorAction SilentlyContinue)) {
    throw "Salesforce CLI ('sf') is not installed or not on PATH."
}

if (-not [System.IO.Path]::IsPathRooted($ManifestPath)) {
    $ManifestPath = Join-Path $SalesforceRoot $ManifestPath
}

if (-not (Test-Path $ManifestPath)) {
    throw "Manifest file not found: $ManifestPath"
}

Push-Location $SalesforceRoot
try {
    & sf project deploy start --manifest $ManifestPath --target-org $TargetOrg
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
param(
    [string]$TargetOrg = "MY_SANDBOX_ALIAS",
    [switch]$Verbose
)

if (-not (Get-Command sf -ErrorAction SilentlyContinue)) {
    throw "Salesforce CLI ('sf') is not installed or not on PATH."
}

$args = @("org", "display", "--target-org", $TargetOrg)

if ($Verbose) {
    $args += "--verbose"
}

& sf @args
exit $LASTEXITCODE
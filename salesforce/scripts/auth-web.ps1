param(
    [string]$Alias = "MY_SANDBOX_ALIAS",
    [string]$InstanceUrl = "https://YOUR_MY_DOMAIN_OR_LOGIN_HOST",
    [switch]$SetDefault,
    [switch]$SetDefaultDevHub
)

if (-not (Get-Command sf -ErrorAction SilentlyContinue)) {
    throw "Salesforce CLI ('sf') is not installed or not on PATH."
}

$args = @("org", "login", "web", "--alias", $Alias, "--instance-url", $InstanceUrl)

if ($SetDefault) {
    $args += "--set-default"
}

if ($SetDefaultDevHub) {
    $args += "--set-default-dev-hub"
}

Write-Host "Opening browser login for alias '$Alias' against '$InstanceUrl'." -ForegroundColor Cyan
& sf @args
exit $LASTEXITCODE
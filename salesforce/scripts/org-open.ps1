param(
    [string]$TargetOrg = "MY_SANDBOX_ALIAS",
    [string]$Path,
    [string]$SourceFile,
    [switch]$UrlOnly,
    [ValidateSet("chrome", "edge", "firefox")]
    [string]$Browser
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SalesforceRoot = Split-Path -Parent $ScriptRoot

if (-not (Get-Command sf -ErrorAction SilentlyContinue)) {
    throw "Salesforce CLI ('sf') is not installed or not on PATH."
}

$args = @("org", "open", "--target-org", $TargetOrg)

if ($Path) {
    $args += @("--path", $Path)
}

if ($SourceFile) {
    if (-not [System.IO.Path]::IsPathRooted($SourceFile)) {
        $candidate = Join-Path $SalesforceRoot $SourceFile
        if (Test-Path $candidate) {
            $SourceFile = $candidate
        }
    }
    $args += @("--source-file", $SourceFile)
}

if ($UrlOnly) {
    $args += "--url-only"
}

if ($Browser) {
    $args += @("--browser", $Browser)
}

& sf @args
exit $LASTEXITCODE
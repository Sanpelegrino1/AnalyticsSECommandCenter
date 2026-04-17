param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [string]$OutputPath,
    [switch]$UseToolingApi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

if (-not $TargetOrg) {
    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

$arguments = @('data', 'query', '--query', $Query, '--target-org', $TargetOrg, '--json')
if ($UseToolingApi) {
    $arguments += '--use-tooling-api'
}

$response = & sf @arguments | ConvertFrom-Json
$records = @($response.result.records | Select-Object -ExcludeProperty attributes)

if ($OutputPath) {
    $resolvedOutputPath = $OutputPath
    if (-not [System.IO.Path]::IsPathRooted($resolvedOutputPath)) {
        $resolvedOutputPath = Resolve-CommandCenterPath $OutputPath
    }

    Ensure-Directory -Path (Split-Path -Parent $resolvedOutputPath)
    $extension = [System.IO.Path]::GetExtension($resolvedOutputPath)
    if ($extension -ieq '.json') {
        $records | ConvertTo-Json -Depth 10 | Set-Content -Path $resolvedOutputPath -Encoding UTF8
    } else {
        $records | Export-Csv -Path $resolvedOutputPath -NoTypeInformation -Encoding UTF8
    }

    Write-Host "Exported $($records.Count) rows to '$resolvedOutputPath'."
} else {
    $records | Format-Table -AutoSize
}

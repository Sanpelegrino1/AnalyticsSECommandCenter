param(
    [string]$TargetKey,
    [Parameter(Mandatory = $true)]
    [ValidateSet('workbook', 'datasource', 'flow', 'project')]
    [string]$ContentType,
    [string]$Id,
    [string]$Name
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

Invoke-TableauSession -TargetKey $TargetKey -ScriptBlock {
    param($context)

    $plural = switch ($ContentType) {
        'workbook' { 'workbooks' }
        'datasource' { 'datasources' }
        'flow' { 'flows' }
        'project' { 'projects' }
    }

    $response = Invoke-TableauApi -Context $context -Method 'Get' -RelativePath "/sites/$($context.SiteId)/$plural?pageSize=1000"
    $nodeName = if ($plural -eq 'datasources') { 'datasource' } else { $ContentType }
    $items = @($response.$plural.$nodeName)

    if ($Id) {
        $items = @($items | Where-Object { $_.id -eq $Id })
    }

    if ($Name) {
        $items = @($items | Where-Object { $_.name -like $Name })
    }

    $items | ConvertTo-Json -Depth 20
}

param(
    [string]$TargetKey,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

Invoke-TableauSession -TargetKey $TargetKey -ScriptBlock {
    param($context)

    $response = Invoke-TableauApi -Context $context -Method 'Get' -RelativePath "/sites/$($context.SiteId)/projects?pageSize=1000"
    $projects = @($response.projects.project)

    if ($Json) {
        $projects | ConvertTo-Json -Depth 10
        return
    }

    $projects |
        Select-Object id, name, description, @{ Name = 'ParentProjectId'; Expression = { $_.parentProjectId } } |
        Sort-Object name |
        Format-Table -AutoSize
}

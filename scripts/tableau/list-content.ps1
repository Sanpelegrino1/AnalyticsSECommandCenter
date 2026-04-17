param(
    [string]$TargetKey,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

Invoke-TableauSession -TargetKey $TargetKey -ScriptBlock {
    param($context)

    $items = New-Object System.Collections.Generic.List[object]

    $workbooks = Invoke-TableauApi -Context $context -Method 'Get' -RelativePath "/sites/$($context.SiteId)/workbooks?pageSize=1000"
    foreach ($item in @($workbooks.workbooks.workbook)) {
        $items.Add([pscustomobject]@{
            ContentType = 'workbook'
            Id = $item.id
            Name = $item.name
            ProjectId = $item.project.id
            OwnerId = $item.owner.id
        })
    }

    $datasources = Invoke-TableauApi -Context $context -Method 'Get' -RelativePath "/sites/$($context.SiteId)/datasources?pageSize=1000"
    foreach ($item in @($datasources.datasources.datasource)) {
        $items.Add([pscustomobject]@{
            ContentType = 'datasource'
            Id = $item.id
            Name = $item.name
            ProjectId = $item.project.id
            OwnerId = $item.owner.id
        })
    }

    $flows = Invoke-TableauApi -Context $context -Method 'Get' -RelativePath "/sites/$($context.SiteId)/flows?pageSize=1000"
    foreach ($item in @($flows.flows.flow)) {
        $items.Add([pscustomobject]@{
            ContentType = 'flow'
            Id = $item.id
            Name = $item.name
            ProjectId = $item.project.id
            OwnerId = $item.owner.id
        })
    }

    if ($Json) {
        $items | ConvertTo-Json -Depth 10
        return
    }

    $items | Sort-Object ContentType, Name | Format-Table -AutoSize
}

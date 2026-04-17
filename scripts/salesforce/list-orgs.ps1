param(
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Assert-CommandAvailable -Name 'sf' -Hint 'Install Salesforce CLI or run the bootstrap script.'

$registryPath = Resolve-CommandCenterPath 'notes/registries/salesforce-orgs.json'
$registry = Read-JsonFile -Path $registryPath
$orgLookup = @{}
foreach ($item in @($registry.orgs)) {
    $orgLookup[$item.alias] = $item
}

$response = & sf org list --json | ConvertFrom-Json
if ($Json) {
    $response | ConvertTo-Json -Depth 10
    exit 0
}

$rows = New-Object System.Collections.Generic.List[object]
foreach ($org in @($response.result.nonScratchOrgs) + @($response.result.scratchOrgs)) {
    $metadata = $null
    if ($org.alias -and $orgLookup.ContainsKey($org.alias)) {
        $metadata = $orgLookup[$org.alias]
    }

    $rows.Add([pscustomobject]@{
        Alias = $org.alias
        Username = $org.username
        OrgId = $org.orgId
        ConnectedStatus = $org.connectedStatus
        IsDefaultUsername = $org.isDefaultUsername
        IsDefaultDevHubUsername = $org.isDefaultDevHubUsername
        LoginUrl = if ($metadata) { $metadata.loginUrl } else { '' }
        Purpose = if ($metadata) { $metadata.purpose } else { '' }
        Notes = if ($metadata) { $metadata.notes } else { '' }
    })
}

$rows | Sort-Object Alias | Format-Table -AutoSize

[CmdletBinding()]
param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceDeveloperName,
    [string]$WorkspaceLabel,
    [string]$Description,
    [string]$OutputPath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_TableauNext.Common.ps1')

$resolvedTargetOrg = Resolve-TableauNextTargetOrg -TargetOrg $TargetOrg
$resolvedWorkspaceLabel = if (-not [string]::IsNullOrWhiteSpace($WorkspaceLabel)) { $WorkspaceLabel } else { $WorkspaceDeveloperName }

$existingWorkspace = @(
    Get-TableauNextWorkspaceRows -TargetOrg $resolvedTargetOrg -Limit 2000 |
        Where-Object { [string]$_.DeveloperName -eq $WorkspaceDeveloperName } |
        Select-Object -First 1
)

$status = 'Created'
if ($existingWorkspace.Count -eq 0) {
    $context = Get-TableauNextAccessContext -TargetOrg $resolvedTargetOrg
    $requestBody = [ordered]@{
        name = $WorkspaceDeveloperName
        label = $resolvedWorkspaceLabel
    }

    if (-not [string]::IsNullOrWhiteSpace($Description)) {
        $requestBody.description = $Description
    }

    $null = Invoke-TableauNextApiRequest -Context $context -Method Post -RelativePath 'tableau/workspaces' -Body $requestBody
    $existingWorkspace = @(
        Get-TableauNextWorkspaceRows -TargetOrg $resolvedTargetOrg -Limit 2000 |
            Where-Object { [string]$_.DeveloperName -eq $WorkspaceDeveloperName } |
            Select-Object -First 1
    )

    if ($existingWorkspace.Count -eq 0) {
        throw "Workspace '$WorkspaceDeveloperName' was created but could not be rediscovered immediately."
    }
} else {
    $status = 'AlreadyExists'
}

$record = [pscustomobject]@{
    Status = $status
    TargetOrg = $resolvedTargetOrg
    WorkspaceId = [string]$existingWorkspace[0].WorkspaceId
    WorkspaceDeveloperName = [string]$existingWorkspace[0].DeveloperName
    WorkspaceLabel = [string]$existingWorkspace[0].Label
    Language = [string]$existingWorkspace[0].Language
    Description = [string]$existingWorkspace[0].Description
    LastModifiedDate = [string]$existingWorkspace[0].LastModifiedDate
}

Write-TableauNextOutput -Records @($record) -OutputPath $OutputPath -Json:$Json -DefaultTableFields @(
    'Status',
    'WorkspaceId',
    'WorkspaceDeveloperName',
    'WorkspaceLabel',
    'LastModifiedDate'
)
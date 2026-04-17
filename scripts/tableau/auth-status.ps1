param(
    [string]$TargetKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_Tableau.Common.ps1')

Invoke-TableauSession -TargetKey $TargetKey -ScriptBlock {
    param($context)

    [pscustomobject]@{
        TargetKey = $context.Config.TargetKey
        ServerUrl = $context.Config.ServerUrl
        SiteContentUrl = $context.Config.SiteContentUrl
        SiteId = $context.SiteId
        UserId = $context.UserId
        DefaultProjectId = $context.Config.DefaultProjectId
        Authenticated = $true
    } | Format-List
}

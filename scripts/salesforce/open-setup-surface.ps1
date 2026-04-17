param(
    [string]$TargetOrg = $env:SF_DEFAULT_ALIAS,
    [Parameter(Mandatory = $true)]
    [ValidateSet('SetupHome', 'ObjectManager', 'Users', 'PermissionSets', 'PermissionSetGroups', 'LightningApps', 'Flows', 'ConnectedApps', 'InstalledPackages')]
    [string]$Surface
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\CommandCenter.Common.ps1')

Import-CommandCenterEnv
if (-not $TargetOrg) {
    throw 'Provide -TargetOrg or set SF_DEFAULT_ALIAS in .env.local.'
}

$pathMap = @{
    SetupHome = '/lightning/setup/SetupOneHome/home'
    ObjectManager = '/lightning/setup/ObjectManager/home'
    Users = '/lightning/setup/ManageUsers/home'
    PermissionSets = '/lightning/setup/PermSets/home'
    PermissionSetGroups = '/lightning/setup/PermSetGroups/home'
    LightningApps = '/lightning/setup/AppMenu/home'
    Flows = '/lightning/setup/Flows/home'
    ConnectedApps = '/lightning/setup/ConnectedApplication/home'
    InstalledPackages = '/lightning/setup/ImportedPackage/home'
}

& (Join-Path $PSScriptRoot 'open-org.ps1') -TargetOrg $TargetOrg -Path $pathMap[$Surface]
exit $LASTEXITCODE

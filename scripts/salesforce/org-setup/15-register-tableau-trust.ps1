# OrgSetup step (p) -- register this Salesforce org with PACE and PACE-NEXUS Tableau sites.
#
# For each site:
#   1. Signs in via PAT
#   2. Adds the Salesforce org admin user with Explorer role + TableauIDWithMFA auth
#      (username = whichever SF field the org uses as the Tableau identity -- Email or Username)
#   3. Registers the org as a trusted External Authorization Server (EAS)
#   4. Signs out
#
# Idempotent: skips user add if already present; skips EAS if issuer already registered.
# Each site runs independently -- a failure on PACE does not abort PACE-NEXUS.
#
# Inputs:  -Alias, -PatName, -PatSecret  (all required)

param(
    [Parameter(Mandatory = $true)] [string]$Alias,
    [Parameter(Mandatory = $true)] [string]$PatName,
    [Parameter(Mandatory = $true)] [string]$PatSecret
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'lib\OrgSetup.Common.ps1')

Write-Host ''
Write-Host '--- [p] Register with PACE & PACE-NEXUS Tableau sites ---'

$state = Read-OrgSetupState -Alias $Alias
if (@($state.completed) -contains 'p-pace-trust') {
    Write-Host '  Already completed -- skipping.' -ForegroundColor Cyan
    return
}

$auth          = Get-OrgSetupAuth -Alias $Alias
$sfInstanceUrl = $auth.InstanceUrl
$sfJwksUri     = $sfInstanceUrl + '/id/keys'
$easName       = 'Salesforce - ' + $Alias

# ── Determine which SF field value Tableau uses to identify this user ─────────
#
# The "Select Tableau User Identity field" setting in Setup > Tableau LWC Settings
# is not reliably queryable via SOQL or Tooling API. The script defaults to Email
# (the org default) but lets the user override at runtime.

$sfUserEmail = $null
try {
    $userRec = Invoke-OrgSetupSoql -Auth $auth -Soql `
        "SELECT Email, Username FROM User WHERE Username = '$($auth.Username)' LIMIT 1"
    if ($userRec.records -and $userRec.records.Count -gt 0) {
        $sfUserEmail = $userRec.records[0].Email
    }
} catch {}

$defaultIdentity = if ($sfUserEmail) { $sfUserEmail } else { $auth.Username }

Write-Host ''
Write-Host '  Your org has a "Select Tableau User Identity field" setting in Setup >' -ForegroundColor Cyan
Write-Host '  Tableau Lightning Web Components Settings that controls how Tableau matches' -ForegroundColor Cyan
Write-Host '  your Salesforce user. The script will use that value to create your Tableau' -ForegroundColor Cyan
Write-Host '  user, so the two must match.' -ForegroundColor Cyan
Write-Host ''
Write-Host '  Common choices:'
Write-Host "    [1] Email    ($sfUserEmail)"
Write-Host "    [2] Username ($($auth.Username))"
Write-Host '    [3] Other -- enter a custom value'
Write-Host ''
$idChoice = Read-Host "  Which identity field is selected in your org? (1/2/3, default 1)"

switch ($idChoice.Trim()) {
    '2'     { $tabIdentity = $auth.Username }
    '3'     { $tabIdentity = Read-Host '  Enter the exact value to use as the Tableau username' }
    default { $tabIdentity = $defaultIdentity }
}

if (-not $tabIdentity) {
    Write-Host '  No identity value provided -- aborting step.' -ForegroundColor Red
    Add-OrgSetupLogEntry -Alias $Alias -Step 'p-pace-trust' -Outcome 'skipped' `
        -Message 'User did not provide a Tableau identity value.'
    return
}

Write-Host "  Will register Tableau user: $tabIdentity" -ForegroundColor DarkGray

$tableauBase = 'https://prod-uswest-c.online.tableau.com'
$apiVer      = '3.22'

$sites = @(
    [ordered]@{ Label = 'PACE';       ContentUrl = 'pace';       SiteLuid = '5a81db69-14f1-42c7-b6a5-65ec087bf57d' }
    [ordered]@{ Label = 'PACE-NEXUS'; ContentUrl = 'pace-nexus'; SiteLuid = '6901a397-fe8d-4795-83a0-7a6e7685434f' }
)

# ── Tableau REST helpers ──────────────────────────────────────────────────────

function Invoke-TabRest {
    param(
        [string]$Method = 'GET',
        [string]$Uri,
        [hashtable]$Headers = @{},
        [string]$Body = '',
        [switch]$AllowError
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $Headers['Accept'] = 'application/json'
        $params = @{
            Method      = $Method
            Uri         = $Uri
            Headers     = $Headers
            ContentType = 'application/json'
            ErrorAction = 'Stop'
        }
        if ($Body) { $params['Body'] = $Body }
        return Invoke-RestMethod @params
    } catch {
        if ($AllowError) { return $null }
        throw
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

# ── Per-site loop (each site independent -- failure in one does not abort other) ──

$siteResults = @{}

foreach ($site in $sites) {
    $siteResults[$site.Label] = 'failed'
    try {

    Write-Host "  [$($site.Label)] Signing in..."

    # 1. Sign in
    $signinBody = [ordered]@{
        credentials = [ordered]@{
            personalAccessTokenName   = $PatName
            personalAccessTokenSecret = $PatSecret
            site                      = [ordered]@{ contentUrl = $site.ContentUrl }
        }
    } | ConvertTo-Json -Depth 5

    $signin = $null
    try {
        $signin = Invoke-TabRest -Method POST `
            -Uri "$tableauBase/api/$apiVer/auth/signin" `
            -Body $signinBody
    } catch {
        $msg = 'Sign in to ' + $site.Label + ' failed: ' + $_.Exception.Message + '. Check that your PAT is valid and has access to this site.'
        Add-OrgSetupWarning -Alias $Alias -Step 'p-pace-trust' -Feature $site.Label -Message $msg
        Write-Host "  [$($site.Label)] FAILED sign-in: $($_.Exception.Message)" -ForegroundColor Red
        continue
    }

    $token   = $signin.credentials.token
    $siteId  = $signin.credentials.site.id
    $headers = @{ 'X-Tableau-Auth' = $token }

    Write-Host "  [$($site.Label)] Signed in (site $siteId)." -ForegroundColor DarkGray

    # 2. Add user to site (if not already present)
    Write-Host "  [$($site.Label)] Checking for user $tabIdentity..."
    $existingUser = $null
    try {
        $encoded = [Uri]::EscapeDataString($tabIdentity)
        $existingUser = Invoke-TabRest -Method GET `
            -Uri "$tableauBase/api/$apiVer/sites/$siteId/users?filter=name:eq:$encoded" `
            -Headers $headers -AllowError
    } catch {}

    $userFound = $false
    if ($existingUser) {
        $usersProp = $existingUser.PSObject.Properties['users']
        if ($usersProp -and $usersProp.Value) {
            $userProp = $usersProp.Value.PSObject.Properties['user']
            if ($userProp) {
                $userFound = (@($userProp.Value | Where-Object { $_.name -eq $tabIdentity })).Count -gt 0
            }
        }
    }

    if ($userFound) {
        Write-Host "  [$($site.Label)] User already present -- skipping add." -ForegroundColor Cyan
    } else {
        Write-Host "  [$($site.Label)] Adding user $tabIdentity..."
        $addUserBody = [ordered]@{
            user = [ordered]@{
                name        = $tabIdentity
                siteRole    = 'Explorer'
                authSetting = 'TableauIDWithMFA'
            }
        } | ConvertTo-Json -Depth 4

        try {
            $addResult = Invoke-TabRest -Method POST `
                -Uri "$tableauBase/api/$apiVer/sites/$siteId/users" `
                -Headers $headers -Body $addUserBody
            Write-Host "  [$($site.Label)] User added (id=$($addResult.user.id))." -ForegroundColor Green
        } catch {
            $msg = 'Add user to ' + $site.Label + ' failed: ' + $_.Exception.Message
            Add-OrgSetupWarning -Alias $Alias -Step 'p-pace-trust' -Feature $site.Label -Message $msg
            Write-Host "  [$($site.Label)] WARNING: could not add user -- $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    # 3. Register org as External Authorization Server (EAS)
    Write-Host "  [$($site.Label)] Checking for existing EAS ($sfInstanceUrl)..."

    $existingEas = Invoke-TabRest -Method GET `
        -Uri "$tableauBase/api/$apiVer/sites/$siteId/connected-apps/external-authorization-servers" `
        -Headers $headers -AllowError

    $easFound = $false
    if ($existingEas) {
        $easContainerProp = $existingEas.PSObject.Properties['externalAuthorizationServers']
        if ($easContainerProp -and $easContainerProp.Value) {
            $easItemProp = $easContainerProp.Value.PSObject.Properties['externalAuthorizationServer']
            if ($easItemProp) {
                $easFound = (@($easItemProp.Value) | Where-Object { $_.issuerUrl -eq $sfInstanceUrl }).Count -gt 0
            }
        }
    }

    if ($easFound) {
        Write-Host "  [$($site.Label)] EAS already registered -- skipping." -ForegroundColor Cyan
    } else {
        Write-Host "  [$($site.Label)] Registering EAS..."
        $easBody = [ordered]@{
            externalAuthorizationServer = [ordered]@{
                name      = $easName
                issuerUrl = $sfInstanceUrl
                jwksUri   = $sfJwksUri
                enabled   = $true
            }
        } | ConvertTo-Json -Depth 4

        try {
            $easResult = Invoke-TabRest -Method POST `
                -Uri "$tableauBase/api/$apiVer/sites/$siteId/connected-apps/external-authorization-servers" `
                -Headers $headers -Body $easBody
            Write-Host "  [$($site.Label)] EAS registered (id=$($easResult.externalAuthorizationServer.id))." -ForegroundColor Green
        } catch {
            $msg = 'EAS registration on ' + $site.Label + ' failed: ' + $_.Exception.Message + '. Register manually at: ' + $tableauBase + '/#/site/' + $site.ContentUrl + '/connectedApplications'
            Add-OrgSetupWarning -Alias $Alias -Step 'p-pace-trust' -Feature $site.Label -Message $msg
            Write-Host "  [$($site.Label)] WARNING: EAS registration failed -- $($_.Exception.Message)" -ForegroundColor Yellow
            continue
        }
    }

    # 4. Sign out
    try {
        Invoke-TabRest -Method DELETE `
            -Uri "$tableauBase/api/$apiVer/auth/signout" `
            -Headers $headers -AllowError | Out-Null
    } catch {}

    Write-Host "  [$($site.Label)] Done." -ForegroundColor Green
    $siteResults[$site.Label] = 'ok'

    } catch {
        # Catch-all so a crash on PACE never aborts PACE-NEXUS
        $msg = 'Unexpected error on ' + $site.Label + ': ' + $_.Exception.Message
        Add-OrgSetupWarning -Alias $Alias -Step 'p-pace-trust' -Feature $site.Label -Message $msg
        Write-Host "  [$($site.Label)] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$anyFailure = (@($siteResults.Values | Where-Object { $_ -ne 'ok' })).Count -gt 0

if (-not $anyFailure) {
    Add-OrgSetupLogEntry -Alias $Alias -Step 'p-pace-trust' -Outcome 'completed' `
        -Message "Registered $tabIdentity and EAS ($sfInstanceUrl) on PACE and PACE-NEXUS."
    Write-Host '  PACE and PACE-NEXUS configured.' -ForegroundColor Green
} else {
    Add-OrgSetupLogEntry -Alias $Alias -Step 'p-pace-trust' -Outcome 'failed' `
        -Message 'One or more Tableau site registrations failed -- see warnings.'
    Write-Host '  Some registrations failed. See warnings in the report.' -ForegroundColor Yellow
}

Write-Host '  [p] Done.' -ForegroundColor Green

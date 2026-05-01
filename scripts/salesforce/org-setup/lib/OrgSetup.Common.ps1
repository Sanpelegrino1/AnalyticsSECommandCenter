# OrgSetup shared helpers.
#
# Provides: Tooling API PATCH/POST/GET, REST GET, state-file read/write, step logger.
# All functions assume an authenticated `sf` alias and use `sf org display --json` to
# pull the access token + instance URL just-in-time (no token is ever persisted).

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\..\..\common\CommandCenter.Common.ps1')

function Get-OrgSetupApiVersion {
    return 'v60.0'
}

function Get-OrgSetupPlatform {
    # Returns 'Windows', 'macOS', 'Linux', or 'Unknown'.
    # Windows PowerShell 5.1 doesn't define $IsWindows; anything < 6 is Windows.
    if ($PSVersionTable.PSVersion.Major -lt 6) { return 'Windows' }
    if ($IsWindows) { return 'Windows' }
    if ($IsMacOS)   { return 'macOS' }
    if ($IsLinux)   { return 'Linux' }
    return 'Unknown'
}

function Update-OrgSetupPath {
    # Refresh $env:PATH from persistent sources so newly-installed binaries
    # become visible inside the current process.
    $platform = Get-OrgSetupPlatform
    if ($platform -eq 'Windows') {
        $machine = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
        $user    = [System.Environment]::GetEnvironmentVariable('Path', 'User')
        $env:Path = ($machine, $user | Where-Object { $_ }) -join ';'
    } else {
        # On macOS/Linux, common package managers install into well-known dirs.
        foreach ($p in @('/opt/homebrew/bin','/usr/local/bin','/usr/local/sbin')) {
            if ((Test-Path $p) -and ($env:PATH -notlike "*$p*")) {
                $env:PATH = "$p`:$env:PATH"
            }
        }
    }
}

function Assert-SalesforceCli {
    # Preflight: ensure `sf` is on PATH. If missing, prompt the user (unless
    # -NoPrompt) and install via the platform-native package manager.
    # - Windows: winget install Salesforce.sfdx (retries with admin elevation on failure)
    # - macOS:   brew install salesforce-cli
    # - Linux:   prints manual instructions and throws
    param(
        [switch]$NoPrompt
    )

    if (Get-Command sf -ErrorAction SilentlyContinue) { return }

    $platform = Get-OrgSetupPlatform
    Write-Host ''
    Write-Host 'Salesforce CLI (sf) is required to continue.' -ForegroundColor Yellow
    Write-Host ("  Detected platform: {0}" -f $platform)

    $install = $NoPrompt
    if (-not $NoPrompt) {
        $response = Read-Host 'Install Salesforce CLI now? (y/n)'
        $install = $response -match '^(?i)y(es)?$'
    }
    if (-not $install) {
        throw "Salesforce CLI is required. Install manually: https://developer.salesforce.com/tools/sfdxcli"
    }

    switch ($platform) {
        'Windows' {
            if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
                throw "winget not available. Install Salesforce CLI manually from https://developer.salesforce.com/tools/sfdxcli, or install App Installer from the Microsoft Store and retry."
            }
            Write-Host 'Installing via: winget install Salesforce.sfdx'
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                & winget install --id Salesforce.sfdx --accept-source-agreements --accept-package-agreements --silent 2>&1 | ForEach-Object { Write-Host $_ }
                $winExit = $LASTEXITCODE
            } finally {
                $ErrorActionPreference = $prevEap
            }
            if ($winExit -ne 0) {
                Write-Host 'winget returned non-zero; retrying with admin elevation...' -ForegroundColor Yellow
                $wingetArgs = @('install','--id','Salesforce.sfdx','--accept-source-agreements','--accept-package-agreements','--silent')
                $proc = Start-Process -FilePath 'winget' -ArgumentList $wingetArgs -Verb RunAs -Wait -PassThru
                if ($proc.ExitCode -ne 0) {
                    throw "winget install failed (exit $($proc.ExitCode)). Install manually: https://developer.salesforce.com/tools/sfdxcli"
                }
            }
        }
        'macOS' {
            if (-not (Get-Command brew -ErrorAction SilentlyContinue)) {
                throw "Homebrew not available. Install Homebrew first from https://brew.sh and retry, or install Salesforce CLI manually from https://developer.salesforce.com/tools/sfdxcli"
            }
            Write-Host 'Installing via: brew install salesforce-cli'
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                & brew install salesforce-cli 2>&1 | ForEach-Object { Write-Host $_ }
                $brewExit = $LASTEXITCODE
            } finally {
                $ErrorActionPreference = $prevEap
            }
            if ($brewExit -ne 0) {
                throw "brew install salesforce-cli failed (exit $brewExit). Install manually: https://developer.salesforce.com/tools/sfdxcli"
            }
        }
        default {
            throw "Auto-install not supported on $platform. Install manually: https://developer.salesforce.com/tools/sfdxcli"
        }
    }

    Update-OrgSetupPath
    if (-not (Get-Command sf -ErrorAction SilentlyContinue)) {
        throw "Salesforce CLI installed, but 'sf' is still not on PATH for this shell. Open a new terminal and rerun the script."
    }
    Write-Host 'Salesforce CLI installed successfully.' -ForegroundColor Green
}

function Get-OrgSetupStateDir {
    $dir = Resolve-CommandCenterPath 'notes/org-setup-state'
    Ensure-Directory -Path $dir
    return $dir
}

function Get-OrgSetupStatePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )
    return Join-Path (Get-OrgSetupStateDir) ("{0}.json" -f $Alias)
}

function Read-OrgSetupState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    $path = Get-OrgSetupStatePath -Alias $Alias
    $state = Read-JsonFile -Path $path
    if ($null -eq $state) {
        $state = [pscustomobject]@{
            alias        = $Alias
            createdUtc   = Get-UtcTimestamp
            updatedUtc   = Get-UtcTimestamp
            completed    = @()
            skipped      = @()
            log          = @()
        }
    }
    return $state
}

function Save-OrgSetupState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [object]$State
    )
    $State.updatedUtc = Get-UtcTimestamp
    Write-JsonFile -Path (Get-OrgSetupStatePath -Alias $Alias) -Value $State
}

function Add-OrgSetupWarning {
    # Record a per-step / per-feature warning without halting the run.
    # Surfaced at end of run-resume and persisted in the state file's
    # `warnings` array so it survives across invocations.
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [string]$Step,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string]$Feature = ''
    )

    $state = Read-OrgSetupState -Alias $Alias
    if (-not ($state.PSObject.Properties.Name -contains 'warnings')) {
        $state | Add-Member -NotePropertyName warnings -NotePropertyValue @() -Force
    }
    $entry = [pscustomobject]@{
        step      = $Step
        feature   = $Feature
        message   = $Message
        timestamp = Get-UtcTimestamp
    }
    $state.warnings = @($state.warnings) + $entry
    Save-OrgSetupState -Alias $Alias -State $state

    $suffix = if ($Feature) { " [$Feature]" } else { '' }
    Write-Host ("[WARN] {0,-30}{1} {2}" -f $Step, $suffix, $Message) -ForegroundColor Yellow
}

function Write-OrgSetupRunSummary {
    # Print an end-of-run summary box with any warnings that accrued during
    # the current resume/kickoff invocation. Call as the final step of an
    # orchestrator. `-Since` filters to warnings newer than the given UTC
    # timestamp; pass the run-start timestamp to scope to this invocation.
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [string]$Since = ''
    )

    $state = Read-OrgSetupState -Alias $Alias
    $warnings = @()
    if ($state.PSObject.Properties.Name -contains 'warnings') {
        $warnings = @($state.warnings)
    }
    if ($Since) {
        $warnings = @($warnings | Where-Object { $_.timestamp -ge $Since })
    }

    # Compute latest outcome per step from the log so a step that was first
    # skipped then later completed shows only as completed.
    $latestByStep = @{}
    foreach ($entry in @($state.log)) {
        $latestByStep[$entry.step] = $entry.outcome
    }
    $finalCompleted = @($latestByStep.Keys | Where-Object { $latestByStep[$_] -in @('completed','noop') } | Sort-Object)
    $finalSkipped   = @($latestByStep.Keys | Where-Object { $latestByStep[$_] -eq 'skipped' } | Sort-Object)

    Write-Host ''
    Write-Host '=== OrgSetup Summary ===' -ForegroundColor Cyan
    Write-Host ("Alias:    {0}" -f $Alias)
    Write-Host ("Completed: {0}" -f ($finalCompleted -join ', '))
    if ($finalSkipped.Count -gt 0) {
        Write-Host ("Skipped:   {0}" -f ($finalSkipped -join ', '))
    }
    if ($warnings.Count -gt 0) {
        Write-Host ''
        Write-Host ("!!! {0} warning(s) during this run !!!" -f $warnings.Count) -ForegroundColor Yellow
        foreach ($w in $warnings) {
            $feature = if ($w.feature) { "[$($w.feature)] " } else { '' }
            Write-Host ("  - [{0}] {1}{2}" -f $w.step, $feature, $w.message) -ForegroundColor Yellow
        }
        Write-Host ''
        Write-Host 'Review these manually -- the rest of BUILD 1 is complete.' -ForegroundColor Yellow
    } else {
        Write-Host '(no warnings)' -ForegroundColor Green
    }
    Write-Host ("State file: {0}" -f (Get-OrgSetupStatePath -Alias $Alias))
}

function Add-OrgSetupLogEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [Parameter(Mandatory = $true)]
        [string]$Step,
        [Parameter(Mandatory = $true)]
        [ValidateSet('completed','skipped','failed','noop')]
        [string]$Outcome,
        [string]$Message = ''
    )

    $state = Read-OrgSetupState -Alias $Alias
    $entry = [pscustomobject]@{
        step      = $Step
        outcome   = $Outcome
        message   = $Message
        timestamp = Get-UtcTimestamp
    }
    $state.log = @($state.log) + $entry

    if ($Outcome -eq 'completed' -and ($state.completed -notcontains $Step)) {
        $state.completed = @($state.completed) + $Step
    } elseif ($Outcome -eq 'skipped' -and ($state.skipped -notcontains $Step)) {
        $state.skipped = @($state.skipped) + $Step
    }

    Save-OrgSetupState -Alias $Alias -State $state
    $prefix = switch ($Outcome) {
        'completed' { 'OK  ' }
        'skipped'   { 'SKIP' }
        'failed'    { 'FAIL' }
        'noop'      { 'NOOP' }
    }
    Write-Host ("[{0}] {1,-6} {2}" -f $prefix, $Step, $Message)
}

function Get-OrgSetupAuth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias
    )

    $sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
    # sf writes update-available warnings to stderr; in strict mode those surface
    # as NativeCommandError. Merge streams and filter JSON from the mix.
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $raw = & $sf org display --target-org $Alias --json 2>&1
    } finally {
        $ErrorActionPreference = $previousEap
    }
    if ($LASTEXITCODE -ne 0) {
        throw "sf org display failed for alias '$Alias' (exit $LASTEXITCODE). Run: sf org login web --alias $Alias"
    }
    $jsonText = ($raw | ForEach-Object { $_.ToString() }) -join "`n"
    $startIdx = $jsonText.IndexOf('{')
    if ($startIdx -lt 0) {
        throw "sf org display did not return JSON for alias '$Alias'."
    }
    $display = ($jsonText.Substring($startIdx) | ConvertFrom-Json).result
    if (-not $display.accessToken -or -not $display.instanceUrl) {
        throw "Could not read accessToken/instanceUrl for alias '$Alias'."
    }

    $orgId = $null
    foreach ($prop in @('id','orgId','OrgId')) {
        if ($display.PSObject.Properties.Name -contains $prop) {
            $orgId = $display.$prop
            break
        }
    }
    $userId = $null
    if ($display.PSObject.Properties.Name -contains 'userId') { $userId = $display.userId }

    return [pscustomobject]@{
        Alias       = $Alias
        Username    = $display.username
        OrgId       = $orgId
        InstanceUrl = $display.instanceUrl.TrimEnd('/')
        AccessToken = $display.accessToken
        UserId      = $userId
    }
}

function Invoke-OrgSetupRest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth,
        [Parameter(Mandatory = $true)]
        [ValidateSet('GET','POST','PATCH','DELETE','PUT')]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [object]$Body,
        [switch]$AllowErrorStatus
    )

    $uri = "$($Auth.InstanceUrl)$Path"
    $headers = @{ Authorization = "Bearer $($Auth.AccessToken)" }

    $params = @{
        Uri         = $uri
        Method      = $Method
        Headers     = $headers
        ContentType = 'application/json'
    }

    if ($Body) {
        $params.Body = if ($Body -is [string]) { $Body } else { ($Body | ConvertTo-Json -Depth 20 -Compress) }
    }

    try {
        return Invoke-RestMethod @params
    } catch {
        if ($AllowErrorStatus) {
            return @{
                _error      = $true
                statusCode  = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
                message     = $_.Exception.Message
                body        = try { $_.ErrorDetails.Message } catch { $null }
            }
        }
        throw
    }
}

function Get-OrgSetupUserId {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth
    )

    if ($Auth.UserId) { return $Auth.UserId }

    $api = Get-OrgSetupApiVersion
    $username = [Uri]::EscapeDataString($Auth.Username)
    $query = "SELECT+Id+FROM+User+WHERE+Username='$username'"
    $result = Invoke-OrgSetupRest -Auth $Auth -Method GET -Path "/services/data/$api/query/?q=$query"
    if ($result.records.Count -lt 1) {
        throw "Could not resolve User Id for $($Auth.Username)"
    }
    return $result.records[0].Id
}

function Invoke-OrgSetupSoql {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth,
        [Parameter(Mandatory = $true)]
        [string]$Soql,
        [switch]$Tooling
    )

    $api = Get-OrgSetupApiVersion
    $segment = if ($Tooling) { 'tooling/query' } else { 'query' }
    $escaped = [Uri]::EscapeDataString($Soql)
    return Invoke-OrgSetupRest -Auth $Auth -Method GET -Path "/services/data/$api/$segment/?q=$escaped"
}

function Get-OrgSetupToolingSettingDurableId {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth,
        [Parameter(Mandatory = $true)]
        [string]$SettingsSObject
    )

    $result = Invoke-OrgSetupSoql -Auth $Auth -Tooling -Soql "SELECT DurableId FROM $SettingsSObject"
    if (-not $result.records -or $result.records.Count -lt 1) {
        throw "No $SettingsSObject record found via Tooling API."
    }
    return $result.records[0].DurableId
}

function Set-OrgSetupToolingSettingFlag {
    # Flip a boolean on a *Settings Tooling sObject (e.g., CustomerDataPlatformSettings).
    # Returns $true if the field was changed, $false if it was already in the desired state.
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth,
        [Parameter(Mandatory = $true)]
        [string]$SettingsSObject,
        [Parameter(Mandatory = $true)]
        [string]$FieldName,
        [Parameter(Mandatory = $true)]
        [bool]$Value
    )

    $api = Get-OrgSetupApiVersion
    $current = Invoke-OrgSetupSoql -Auth $Auth -Tooling -Soql "SELECT DurableId, $FieldName FROM $SettingsSObject"
    if (-not $current.records -or $current.records.Count -lt 1) {
        throw "No $SettingsSObject record."
    }
    $record = $current.records[0]
    if ([bool]$record.$FieldName -eq $Value) {
        return $false
    }

    $body = @{}
    $body[$FieldName] = $Value
    $null = Invoke-OrgSetupRest -Auth $Auth -Method PATCH `
        -Path "/services/data/$api/tooling/sobjects/$SettingsSObject/$($record.DurableId)" `
        -Body $body
    return $true
}

function Test-OrgSetupDataCloudReady {
    # Returns $true when Data Cloud tenant provisioning is complete.
    # Signals (any one = ready):
    #   - MktDataConnection sobject describes successfully (200)
    #   - SSOT /data-streams endpoint responds 200
    # The older /ssot/data-connections path 404s in recent API versions and is
    # NOT a reliable signal.
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth
    )

    $api = Get-OrgSetupApiVersion
    $probes = @(
        "/services/data/$api/sobjects/MktDataConnection/describe",
        "/services/data/$api/ssot/data-streams"
    )
    foreach ($p in $probes) {
        $resp = Invoke-OrgSetupRest -Auth $Auth -Method GET -Path $p -AllowErrorStatus
        $isErr = $false
        try { $isErr = [bool]$resp._error } catch {}
        if (-not $isErr) { return $true }
    }
    return $false
}

function Invoke-OrgSetupSfJson {
    # Run `sf ...` with --json and return the parsed .result. Throws on non-zero exit.
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    $sf = Get-RequiredCommandPath -Name 'sf' -Hint 'Install Salesforce CLI.'
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $raw = & $sf @Args --json 2>&1
    } finally {
        $ErrorActionPreference = $previousEap
    }
    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        throw ("sf {0} failed (exit {1}): {2}" -f ($Args -join ' '), $exit, (($raw | ForEach-Object { $_.ToString() }) -join "`n"))
    }
    $jsonText = ($raw | ForEach-Object { $_.ToString() }) -join "`n"
    $startIdx = $jsonText.IndexOf('{')
    if ($startIdx -lt 0) {
        throw "sf did not return JSON. Raw: $jsonText"
    }
    return ($jsonText.Substring($startIdx) | ConvertFrom-Json).result
}

function Invoke-OrgSetupNative {
    # Run a native command tolerating stderr-as-warnings without crashing strict mode.
    # Returns the exit code; streams stdout/stderr to the host.
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments
    )

    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $FilePath @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
    } finally {
        $ErrorActionPreference = $previousEap
    }
    return $LASTEXITCODE
}

function Invoke-OrgSetupNativeWithTimeout {
    # Like Invoke-OrgSetupNative but kills the process after $TimeoutSeconds.
    # Returns the exit code; returns -1 and prints a warning if the timeout was hit.
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$TimeoutSeconds = 600
    )

    $tmpDir     = [System.IO.Path]::GetTempPath()
    $stamp      = [guid]::NewGuid().ToString('N').Substring(0,8)
    $stdoutFile = Join-Path $tmpDir "sf-run-$stamp.out.txt"
    $stderrFile = Join-Path $tmpDir "sf-run-$stamp.err.txt"
    '' | Set-Content $stdoutFile -Encoding UTF8
    '' | Set-Content $stderrFile -Encoding UTF8

    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -RedirectStandardOutput $stdoutFile `
        -RedirectStandardError $stderrFile `
        -NoNewWindow -PassThru

    if (-not $proc) {
        Write-Host "  Could not start process: $FilePath" -ForegroundColor Red
        Remove-Item $stdoutFile, $stderrFile -ErrorAction SilentlyContinue
        return -1
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastOutPos = 0
    $lastErrPos = 0

    while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        if (Test-Path $stdoutFile) {
            $content = Get-Content $stdoutFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($content -and $content.Length -gt $lastOutPos) {
                $chunk = $content.Substring($lastOutPos)
                $lastOutPos = $content.Length
                Write-Host -NoNewline $chunk
            }
        }
        if (Test-Path $stderrFile) {
            $content = Get-Content $stderrFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($content -and $content.Length -gt $lastErrPos) {
                $chunk = $content.Substring($lastErrPos)
                $lastErrPos = $content.Length
                Write-Host -NoNewline $chunk
            }
        }
    }

    if (-not $proc.HasExited) {
        Write-Host ''
        Write-Host "  Command exceeded $TimeoutSeconds s timeout -- killing process." -ForegroundColor Red
        try { $proc.Kill() } catch {}
        Remove-Item $stdoutFile, $stderrFile -ErrorAction SilentlyContinue
        return -1
    }

    # Drain any remaining output
    if (Test-Path $stdoutFile) {
        $content = Get-Content $stdoutFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($content -and $content.Length -gt $lastOutPos) {
            Write-Host -NoNewline $content.Substring($lastOutPos)
        }
    }
    if (Test-Path $stderrFile) {
        $content = Get-Content $stderrFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($content -and $content.Length -gt $lastErrPos) {
            Write-Host -NoNewline $content.Substring($lastErrPos)
        }
    }
    Write-Host ''

    $code = $proc.ExitCode
    Remove-Item $stdoutFile, $stderrFile -ErrorAction SilentlyContinue
    return $code
}

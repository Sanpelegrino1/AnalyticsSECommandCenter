param(
    [string]$Alias = "MY_SANDBOX_ALIAS",
    [string]$InstanceUrl = "https://YOUR_MY_DOMAIN_OR_LOGIN_HOST",
    [string]$ClientId,
    [string]$Scopes,
    [switch]$SetDefault,
    [switch]$SetDefaultDevHub
)

. (Join-Path $PSScriptRoot '..\..\scripts\common\CommandCenter.Common.ps1')

function ConvertTo-ProcessArgumentString {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Values
    )

    $quotedValues = foreach ($value in $Values) {
        if ($value -match '[\s"]') {
            '"{0}"' -f ($value -replace '"', '\"')
        } else {
            $value
        }
    }

    return ($quotedValues -join ' ')
}

$sfCommand = Get-RequiredCommandPath -Name 'sf' -Hint "Install Salesforce CLI or run the bootstrap script."
$salesforceProjectRoot = Resolve-CommandCenterPath 'salesforce'

$loginParameters = @("org", "login", "web", "--alias", $Alias, "--instance-url", $InstanceUrl)

if (-not [string]::IsNullOrWhiteSpace($ClientId)) {
    $loginParameters += @("--client-id", $ClientId)
}

if (-not [string]::IsNullOrWhiteSpace($Scopes)) {
    $loginParameters += @("--scopes", $Scopes)
}

if ($SetDefault) {
    $loginParameters += "--set-default"
}

if ($SetDefaultDevHub) {
    $loginParameters += "--set-default-dev-hub"
}

Write-Host "Opening browser login for alias '$Alias' against '$InstanceUrl'." -ForegroundColor Cyan
Push-Location $salesforceProjectRoot
try {
    if (-not [string]::IsNullOrWhiteSpace($ClientId)) {
        $quotedCommand = '"{0}" {1}' -f $sfCommand, (ConvertTo-ProcessArgumentString -Values $loginParameters)
        $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processStartInfo.FileName = $env:ComSpec
        $processStartInfo.Arguments = '/d /c "{0}"' -f $quotedCommand
        $processStartInfo.WorkingDirectory = $salesforceProjectRoot
        $processStartInfo.UseShellExecute = $false
        $processStartInfo.RedirectStandardInput = $true
        $processStartInfo.RedirectStandardOutput = $true
        $processStartInfo.RedirectStandardError = $true

        $process = [System.Diagnostics.Process]::Start($processStartInfo)
        try {
            $process.StandardInput.WriteLine('')
            $process.StandardInput.Flush()
            $process.StandardInput.Close()
            $standardOutput = $process.StandardOutput.ReadToEnd()
            $standardError = $process.StandardError.ReadToEnd()
            $process.WaitForExit()

            if (-not [string]::IsNullOrWhiteSpace($standardOutput)) {
                Write-Host $standardOutput.TrimEnd()
            }

            if (-not [string]::IsNullOrWhiteSpace($standardError)) {
                Write-Error $standardError.TrimEnd()
            }
        } finally {
            $process.Dispose()
        }

        exit $process.ExitCode
    } else {
        & $sfCommand @loginParameters
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
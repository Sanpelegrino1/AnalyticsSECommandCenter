function Assert-PythonAndPlaywright {
    # Ensures Python 3 and playwright are available.
    # Returns the python executable path if ready, $false otherwise.

    $python = $null
    foreach ($cmd in @('python','python3')) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) {
            # Skip the Windows Store stub (WindowsApps\python*.exe) -- it is not a real install
            if ($found.Source -match 'WindowsApps') { continue }
            $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            $ver = & $found.Source --version 2>&1
            $ErrorActionPreference = $prevEap
            if ($ver -match 'Python 3') { $python = $found.Source; break }
        }
    }

    if (-not $python) {
        Write-Host '  Python 3 is not installed.' -ForegroundColor Yellow
        $platform = Get-OrgSetupPlatform
        $installed = $false
        switch ($platform) {
            'Windows' {
                if (Get-Command winget -ErrorAction SilentlyContinue) {
                    $response = Read-Host '  Install Python 3 now via winget? (y/n)'
                    if ($response -match '^(?i)y(es)?$') {
                        Write-Host '  Installing via: winget install Python.Python.3.12'
                        $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                        & winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent 2>&1 | ForEach-Object { Write-Host "    $_" }
                        $wgExit = $LASTEXITCODE
                        $ErrorActionPreference = $prevEap
                        if ($wgExit -eq 0) { $installed = $true }
                    }
                } else {
                    Write-Host '  winget not available -- install Python manually from https://www.python.org/downloads/' -ForegroundColor Yellow
                }
            }
            'macOS' {
                if (Get-Command brew -ErrorAction SilentlyContinue) {
                    $response = Read-Host '  Install Python 3 now via Homebrew? (y/n)'
                    if ($response -match '^(?i)y(es)?$') {
                        Write-Host '  Installing via: brew install python@3.12'
                        $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                        & brew install python@3.12 2>&1 | ForEach-Object { Write-Host "    $_" }
                        $brewExit = $LASTEXITCODE
                        $ErrorActionPreference = $prevEap
                        if ($brewExit -eq 0) { $installed = $true }
                    }
                } else {
                    Write-Host '  Homebrew not available -- install from https://brew.sh or Python from https://www.python.org/downloads/' -ForegroundColor Yellow
                }
            }
            default {
                Write-Host '  Install Python manually from https://www.python.org/downloads/' -ForegroundColor Yellow
            }
        }

        if (-not $installed) {
            Write-Host '  Continuing without Python -- Feature Manager step will fall back to opening a browser for manual enablement.' -ForegroundColor Yellow
            return $false
        }

        Update-OrgSetupPath
        foreach ($cmd in @('python','python3')) {
            $found = Get-Command $cmd -ErrorAction SilentlyContinue
            if ($found -and $found.Source -notmatch 'WindowsApps') {
                $python = $found.Source; break
            }
        }
        if (-not $python) {
            Write-Host '  Python installed, but not yet on PATH for this shell. Open a new terminal and rerun.' -ForegroundColor Yellow
            return $false
        }
        Write-Host "  Python installed: $python" -ForegroundColor Green
    }

    Write-Host "  Python found: $python" -ForegroundColor Green

    $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $pwCheck = & $python -c "import playwright; print('ok')" 2>&1
    $ErrorActionPreference = $prevEap

    if ($pwCheck -notmatch 'ok') {
        Write-Host '  Playwright not installed. Installing...' -ForegroundColor Yellow
        $prevEap2 = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        & $python -m pip install playwright 2>&1 | ForEach-Object { Write-Host "    $_" }
        $pipExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEap2
        if ($pipExit -ne 0) {
            Write-Host '  pip install playwright failed.' -ForegroundColor Red
            return $false
        }
    }

    Write-Host '  Ensuring Playwright Chromium browser is installed...' -ForegroundColor Yellow
    $prevEap3 = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & $python -m playwright install chromium 2>&1 | ForEach-Object { Write-Host "    $_" }
    $ErrorActionPreference = $prevEap3

    Write-Host '  Python + Playwright ready.' -ForegroundColor Green
    return $python
}

function Invoke-FeatureManagerHeadless {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Auth,
        [Parameter(Mandatory = $true)]
        [string[]]$Features,
        [string]$Python,
        [int]$TimeoutSeconds = 180
    )

    $scriptPath  = Join-Path $PSScriptRoot 'flip_feature_manager.py'
    $featuresCsv = $Features -join ','

    $tmpDir     = [System.IO.Path]::GetTempPath()
    $stdoutFile = Join-Path $tmpDir "fm_stdout_$PID.txt"
    $stderrFile = Join-Path $tmpDir "fm_stderr_$PID.txt"
    '' | Set-Content $stdoutFile -Encoding UTF8
    '' | Set-Content $stderrFile -Encoding UTF8

    Write-Host "  Launching headless browser to flip $($Features.Count) feature(s)..." -ForegroundColor Cyan

    # Write args to a JSON file -- avoids all shell quoting issues with tokens
    $argsFile = Join-Path $tmpDir "fm_args_$PID.json"
    @{
        instance_url = $Auth.InstanceUrl
        access_token = $Auth.AccessToken
        features     = $featuresCsv
        debug        = $true
    } | ConvertTo-Json | Set-Content $argsFile -Encoding UTF8

    $argList = @($scriptPath, '--args-file', $argsFile)

    $proc = Start-Process `
        -FilePath        $Python `
        -ArgumentList    $argList `
        -RedirectStandardOutput $stdoutFile `
        -RedirectStandardError  $stderrFile `
        -NoNewWindow `
        -PassThru

    if (-not $proc) {
        Write-Host '  Failed to start Python process.' -ForegroundColor Red
        return $null
    }

    # Poll stderr file and stream lines live while the process runs
    $lastPos  = 0
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 300
        $lastPos = _StreamNewLines -FilePath $stderrFile -LastPos $lastPos
    }

    if (-not $proc.HasExited) {
        Write-Host "  Headless browser timed out after $TimeoutSeconds s - killing." -ForegroundColor Red
        try { $proc.Kill() } catch {}
        return $null
    }

    # Drain any remaining stderr output
    _StreamNewLines -FilePath $stderrFile -LastPos $lastPos | Out-Null

    # Parse JSON result from stdout
    $jsonLine = $null
    if (Test-Path $stdoutFile) {
        $jsonLine = Get-Content $stdoutFile -Encoding UTF8 |
            Where-Object { $_ -match '^\{' } |
            Select-Object -Last 1
    }

    Remove-Item $stdoutFile, $stderrFile, $argsFile -ErrorAction SilentlyContinue

    if (-not $jsonLine) {
        Write-Host '  Headless script produced no JSON output.' -ForegroundColor Red
        return $null
    }

    try {
        return $jsonLine | ConvertFrom-Json
    } catch {
        Write-Host '  Could not parse headless script JSON output.' -ForegroundColor Red
        return $null
    }
}

function _StreamNewLines {
    param([string]$FilePath, [int]$LastPos)
    if (-not (Test-Path $FilePath)) { return $LastPos }
    try {
        $content = Get-Content $FilePath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if (-not $content -or $content.Length -le $LastPos) { return $LastPos }
        $chunk = $content.Substring($LastPos)
        $newPos = $content.Length
        foreach ($line in ($chunk -split "`n")) {
            $line = $line.TrimEnd("`r")
            if (-not $line) { continue }
            $color = if ($line -match '^\[error\]') { 'Red' } `
                     elseif ($line -match '^\[warn\]')  { 'Yellow' } `
                     else { 'DarkGray' }
            Write-Host "    $line" -ForegroundColor $color
        }
        return $newPos
    } catch {
        return $LastPos
    }
}

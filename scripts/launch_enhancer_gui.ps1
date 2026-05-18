param(
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path ([System.IO.Path]::GetTempPath()) "codex-enhancer-launcher.log"

try {
    Set-Content -LiteralPath $LogPath -Value "" -Encoding UTF8
} catch {
    $LogPath = $null
}

function Write-LauncherLog {
    param(
        [string]$Message
    )

    if (-not $LogPath) {
        return
    }

    try {
        Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) $Message" -Encoding UTF8
    } catch {
        return
    }
}

function Show-LauncherError {
    param(
        [string]$Message
    )

    Write-LauncherLog "ERROR $Message"
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            "Codex Enhancer Installer",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    } catch {
        [Console]::Error.WriteLine($Message)
    }
}

function Resolve-PythonCommand {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-LauncherLog "Probe skipped: $Command not found."
        return $null
    }

    try {
        $global:LASTEXITCODE = 0
        $probeArguments = @($Arguments + @("-c", "import sys; print(sys.executable)"))
        $probeOutput = & $Command @probeArguments 2>&1
        $exitCode = $global:LASTEXITCODE
        if ($null -ne $exitCode -and $exitCode -ne 0) {
            Write-LauncherLog "Probe $Command $($probeArguments -join ' ') -> exit $exitCode output=$($probeOutput -join ' ')"
            return $null
        }
        $runtimePath = ($probeOutput | Where-Object { $_ } | Select-Object -First 1).ToString().Trim()
        if (-not $runtimePath) {
            Write-LauncherLog "Probe $Command $($probeArguments -join ' ') returned no Python executable path."
            return $null
        }
        $resolvedPath = (Resolve-Path -LiteralPath $runtimePath -ErrorAction Stop).Path
        Write-LauncherLog "Probe $Command $($probeArguments -join ' ') -> $resolvedPath."
        return [PSCustomObject]@{
            ProbeCommand = $Command
            ProbeArguments = $probeArguments
            RuntimePath = $resolvedPath
        }
    } catch {
        Write-LauncherLog "Probe $Command failed: $($_.Exception.Message)"
        return $null
    }
}

function Quote-ProcessArgument {
    param(
        [string]$Value
    )

    return '"' + ($Value -replace '"', '\"') + '"'
}

function Start-Installer {
    param(
        [string]$PythonPath
    )

    try {
        Set-Location -LiteralPath $RepoRoot
        $stdoutPath = Join-Path ([System.IO.Path]::GetTempPath()) "codex-enhancer-gui.stdout.log"
        $stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) "codex-enhancer-gui.stderr.log"
        Set-Content -LiteralPath $stdoutPath -Value "" -Encoding UTF8
        Set-Content -LiteralPath $stderrPath -Value "" -Encoding UTF8

        $process = Start-Process `
            -FilePath $PythonPath `
            -ArgumentList @((Quote-ProcessArgument $GuiScript)) `
            -WorkingDirectory $RepoRoot `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -PassThru
        Write-LauncherLog "Started GUI process $($process.Id) with $PythonPath."

        Start-Sleep -Milliseconds 1200
        $process.Refresh()
        if ($process.HasExited) {
            $stdout = Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue
            $stderr = Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue
            $details = (($stderr, $stdout) -join "`n").Trim()
            if (-not $details) {
                $details = "No Python output was captured. See $stderrPath and $stdoutPath."
            }
            throw "The GUI process exited immediately with code $($process.ExitCode).`n`n$details"
        }
    } catch {
        Show-LauncherError "Codex Enhancer could not start the GUI installer.`n`n$($_.Exception.Message)"
        exit 1
    }
}

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$GuiScript = Join-Path $RepoRoot "scripts\install_enhancer_qt_gui.py"
# install_enhancer_qt_gui.py falls back to install_enhancer_web_gui.py when Qt is unavailable.
Write-LauncherLog "RepoRoot=$RepoRoot"
Write-LauncherLog "GuiScript=$GuiScript"

if (-not (Test-Path -LiteralPath $GuiScript -PathType Leaf)) {
    Show-LauncherError "Codex Enhancer could not find the GUI script:`n`n$GuiScript"
    exit 1
}

$candidates = @(
    @{
        Command = "python"
        Arguments = @()
    },
    @{
        Command = "python3"
        Arguments = @()
    },
    @{
        Command = "py"
        Arguments = @("-3")
    }
)

foreach ($candidate in $candidates) {
    $resolved = Resolve-PythonCommand $candidate.Command $candidate.Arguments
    if ($resolved) {
        Write-Host "Starting Codex Enhancer GUI installer with $($resolved.RuntimePath)."
        Start-Installer $resolved.RuntimePath
        exit 0
    }
}

Show-LauncherError @"
Python was not found from PowerShell.

Open PowerShell in this folder and run:
  Get-Command python
  python scripts\install_enhancer_qt_gui.py

If that works, send the output of Get-Command python so this launcher can be taught that Python location.
"@
exit 1

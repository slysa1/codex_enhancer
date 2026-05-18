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

function Test-PythonCommand {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-LauncherLog "Probe skipped: $Command not found."
        return $false
    }

    try {
        $global:LASTEXITCODE = 0
        & $Command @Arguments | Out-Null
        $success = $null -eq $global:LASTEXITCODE -or $global:LASTEXITCODE -eq 0
        Write-LauncherLog "Probe $Command $($Arguments -join ' ') -> exit $global:LASTEXITCODE success=$success."
        return $success
    } catch {
        Write-LauncherLog "Probe $Command failed: $($_.Exception.Message)"
        return $false
    }
}

function Invoke-Installer {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        Set-Location -LiteralPath $RepoRoot
        $global:LASTEXITCODE = 0
        Write-LauncherLog "Invoking $Command $($Arguments -join ' ')"
        & $Command @Arguments
        if ($null -ne $global:LASTEXITCODE -and $global:LASTEXITCODE -ne 0) {
            throw "The installer process exited with code $global:LASTEXITCODE."
        }
        Write-LauncherLog "Installer command returned exit $global:LASTEXITCODE."
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
        Command = "py"
        Arguments = @("-3", $GuiScript)
        ProbeCommand = "py"
        ProbeArguments = @("-3", "-c", "import sys")
    },
    @{
        Command = "python3"
        Arguments = @($GuiScript)
        ProbeCommand = "python3"
        ProbeArguments = @("-c", "import sys")
    },
    @{
        Command = "python"
        Arguments = @($GuiScript)
        ProbeCommand = "python"
        ProbeArguments = @("-c", "import sys")
    },
    @{
        Command = "pyw"
        Arguments = @("-3", $GuiScript)
        ProbeCommand = "pyw"
        ProbeArguments = @("-3", "-c", "import sys")
    },
    @{
        Command = "pythonw"
        Arguments = @($GuiScript)
        ProbeCommand = "pythonw"
        ProbeArguments = @("-c", "import sys")
    }
)

foreach ($candidate in $candidates) {
    if (Test-PythonCommand $candidate.ProbeCommand $candidate.ProbeArguments) {
        Write-Host "Starting Codex Enhancer GUI installer with $($candidate.Command)."
        Invoke-Installer $candidate.Command $candidate.Arguments
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

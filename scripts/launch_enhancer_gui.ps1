param(
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"

function Show-LauncherError {
    param(
        [string]$Message
    )

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
        return $false
    }

    try {
        $global:LASTEXITCODE = 0
        & $Command @Arguments | Out-Null
        return $null -eq $global:LASTEXITCODE -or $global:LASTEXITCODE -eq 0
    } catch {
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
        & $Command @Arguments
        if ($null -ne $global:LASTEXITCODE -and $global:LASTEXITCODE -ne 0) {
            throw "The installer process exited with code $global:LASTEXITCODE."
        }
    } catch {
        Show-LauncherError "Codex Enhancer could not start the browser installer.`n`n$($_.Exception.Message)"
        exit 1
    }
}

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$GuiScript = Join-Path $RepoRoot "scripts\install_enhancer_web_gui.py"

if (-not (Test-Path -LiteralPath $GuiScript -PathType Leaf)) {
    Show-LauncherError "Codex Enhancer could not find the browser GUI script:`n`n$GuiScript"
    exit 1
}

$candidates = @(
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
    },
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
    }
)

foreach ($candidate in $candidates) {
    if (Test-PythonCommand $candidate.ProbeCommand $candidate.ProbeArguments) {
        Invoke-Installer $candidate.Command $candidate.Arguments
        exit 0
    }
}

Show-LauncherError @"
Python was not found from PowerShell.

Open PowerShell in this folder and run:
  Get-Command python
  python scripts\install_enhancer_web_gui.py

If that works, send the output of Get-Command python so this launcher can be taught that Python location.
"@
exit 1

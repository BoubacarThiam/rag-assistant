# Start the demo watchdog (deploy/watchdog.py) at every Windows sign-in, without a window.
#   Install:    powershell -ExecutionPolicy Bypass -File deploy/install-watchdog.ps1
#   Uninstall:  powershell -ExecutionPolicy Bypass -File deploy/install-watchdog.ps1 -Uninstall
param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$TaskName = "RAG Assistant - surveillance de la demo"
$Root = Split-Path -Parent $PSScriptRoot

if ($Uninstall) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Surveillance desinstallee."
    exit 0
}

# pythonw = Python without a console window. The backend virtualenv is created by `uv sync`.
$Pythonw = Join-Path $Root "backend\.venv\Scripts\pythonw.exe"
if (-not (Test-Path $Pythonw)) { throw "Introuvable : $Pythonw (lancer 'uv sync' dans backend/)." }

$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "deploy\watchdog.py" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Garde la demo en ligne et le lien court a jour (deploy/watchdog.py)." -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Output "Surveillance installee et demarree. Journal : $Root\demo-watchdog.log"

# Sets up the nightly "Wilds Atlas" task: it renders every world in config.toml and publishes the atlas, without a window.
# Run schedule.bat again to change the time, e.g. schedule.bat 03:00
param([string]$At = '04:30')
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$python = & python -c 'import sys; print(sys.executable)'
if ($LASTEXITCODE -or -not $python) { throw 'Python was not found. Install Python 3.11+ and tick "Add python.exe to PATH".' }
$pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = $python }
New-Item -ItemType Directory -Force (Join-Path $root 'cache') | Out-Null

$task = @{
  TaskName    = 'Wilds Atlas'
  Description = 'Renders the worlds and publishes the Wilds Atlas. Log: cache\nightly.log'
  Action      = New-ScheduledTaskAction -Execute "`"$pythonw`"" -Argument 'tools\atlas.py publish --log cache\nightly.log' -WorkingDirectory $root
  Trigger     = New-ScheduledTaskTrigger -Daily -At $At
  Settings    = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
}
Register-ScheduledTask @task -Force | Out-Null
Write-Host "Done. The atlas will update every night at $At, and log the last run to cache\nightly.log."
Write-Host 'To remove the task: schtasks /Delete /TN "Wilds Atlas" /F'

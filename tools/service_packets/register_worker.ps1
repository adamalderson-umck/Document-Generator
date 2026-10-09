param([Parameter(Mandatory=$true)][string]$PythonExe,
      [Parameter(Mandatory=$true)][string]$SpoolRoot,
      [string]$TaskName = 'Codex_ServicePacketDesktopWorker')
$ErrorActionPreference = 'Stop'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) { throw 'Task already exists; refusing replacement' }
$python = (Get-Item -LiteralPath $PythonExe).FullName
$spool = (Get-Item -LiteralPath $SpoolRoot).FullName
$runner = Join-Path $PSScriptRoot 'run_queued_job.ps1'
foreach ($value in @($python,$spool,$runner)) { if ($value.Contains('"')) { throw 'Invalid quoted path' } }
$powershell = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$arguments = '-NoProfile -WindowStyle Hidden -File "' + $runner + '" -PythonExe "' + $python + '" -SpoolRoot "' + $spool + '"'
$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
# No trigger: an explicit native Task Scheduler RegisteredTask.Run dispatch starts this worker.
Register-ScheduledTask -TaskName $TaskName -Action $action -Principal $principal -Settings $settings -Description 'On-demand service packet desktop worker; no weekly timer.' | Out-Null
Get-ScheduledTask -TaskName $TaskName

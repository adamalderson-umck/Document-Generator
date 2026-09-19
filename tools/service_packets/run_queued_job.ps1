param([Parameter(Mandatory=$true)][string]$PythonExe,
      [Parameter(Mandatory=$true)][string]$SpoolRoot)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Set-Location -LiteralPath $repo
& $PythonExe -m service_packets.scheduled $SpoolRoot *> (Join-Path $SpoolRoot 'scheduled-run.log')
exit $LASTEXITCODE

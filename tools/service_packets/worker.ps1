param([Parameter(Mandatory=$true)][string]$RequestPath,
      [Parameter(Mandatory=$true)][string]$ApprovedRoot)
$ErrorActionPreference = 'Stop'
$job = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
if ($job.id -notmatch '^[A-Za-z0-9_-]{1,100}$') { throw 'Invalid job id' }
$formats = @{proof_idml='idml'; proof_docx='docx'; export_final_idml='indd'}
if ($job.operation -ne 'collect_outlook' -and -not $formats.ContainsKey($job.operation)) { throw 'Unsupported operation' }
$root = [IO.Path]::GetFullPath($ApprovedRoot).TrimEnd('\') + '\'
foreach ($field in @('input','output','result')) {
    $path = [IO.Path]::GetFullPath($job.$field)
    if (-not $path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw 'Outside approved root' }
    $cursor = $path
    while ($cursor) {
        if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse path rejected' }
        $cursor = Split-Path -Parent $cursor
    }
}
if ((Test-Path -LiteralPath $job.output) -or (Test-Path -LiteralPath $job.result)) { throw 'Destination exists' }
if ((Get-FileHash -LiteralPath $job.input -Algorithm SHA256).Hash.ToLowerInvariant() -ne $job.input_hash) { throw 'Input hash mismatch' }
if ([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($job.deadline)) { throw 'Job expired' }
$result = @{id=$job.id; operation=$job.operation; input_hash=$job.input_hash; status='complete'}
if ($job.operation -eq 'collect_outlook') {
    & (Join-Path $PSScriptRoot 'collect_outlook.ps1') -RequestPath $RequestPath -ApprovedRoot $ApprovedRoot
} else {
    $nativePath = Join-Path $ApprovedRoot ($job.id + '-native-request.json')
    $nativeResult = Join-Path $ApprovedRoot ($job.id + '-native-result.json')
    if ((Test-Path -LiteralPath $nativePath) -or (Test-Path -LiteralPath $nativeResult)) { throw 'Native job already exists' }
    @{id=$job.id; format=$formats[$job.operation]; input=$job.input; output=$job.output;
      result=$nativeResult; sha256=$job.input_hash; deadline=$job.deadline} |
        ConvertTo-Json | Set-Content -LiteralPath $nativePath -Encoding UTF8
    & (Join-Path $PSScriptRoot 'proof.ps1') -RequestPath $nativePath -ApprovedRoot $ApprovedRoot | Out-Null
    $native = Get-Content -LiteralPath $nativeResult -Raw | ConvertFrom-Json
    $result.native = $native
    if ($native.proof_status -eq 'pending') { $result.status='pending'; $result.reason=$native.reason }
}
if ($result.status -eq 'complete') { $result.output_hash=(Get-FileHash -LiteralPath $job.output -Algorithm SHA256).Hash.ToLowerInvariant() }
$temporary = $job.result + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $temporary -Encoding UTF8
[IO.File]::Move($temporary, $job.result)

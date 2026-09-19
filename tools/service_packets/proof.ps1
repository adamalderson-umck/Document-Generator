param(
    [Parameter(Mandatory=$true)][string]$RequestPath,
    [Parameter(Mandatory=$true)][string]$ApprovedRoot
)
$ErrorActionPreference = 'Stop'
$job = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
$root = [IO.Path]::GetFullPath($ApprovedRoot).TrimEnd('\') + '\'
foreach ($field in @('input', 'output', 'result')) {
    $resolved = [IO.Path]::GetFullPath($job.$field)
    if (-not $resolved.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path outside approved proof root' }
    $cursor = Split-Path -Parent $resolved
    while ($cursor -and $cursor.StartsWith($root.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
        if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse path not allowed' }
        $cursor = Split-Path -Parent $cursor
    }
}
if (Test-Path -LiteralPath $job.output) { throw 'Proof output already exists' }
if (Test-Path -LiteralPath $job.result) { throw 'Proof result already exists' }
if ((Get-Item -LiteralPath $job.input).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse input not allowed' }
if ((Get-FileHash -LiteralPath $job.input -Algorithm SHA256).Hash.ToLowerInvariant() -ne $job.sha256) { throw 'Input hash mismatch' }
if ([DateTimeOffset]::UtcNow -gt [DateTimeOffset]::Parse($job.deadline)) { throw 'Proof deadline expired' }
$result = @{id=$job.id; input_hash=$job.sha256; proof_status='pending'; format=$job.format}
if ($job.format -in @('idml', 'indd')) {
    $app = New-Object -ComObject InDesign.Application.2026
    if ($app.Documents.Count -ne 0) {
        $result.reason = 'user_documents_open'
    } else {
        $scriptName = if ($job.format -eq 'indd') { 'export_final_idml.jsx' } else { 'proof_indesign.jsx' }
        $script = 'var job = ' + ($job | ConvertTo-Json -Compress) + ';' + [Environment]::NewLine + (Get-Content -LiteralPath (Join-Path $PSScriptRoot $scriptName) -Raw)
        $stats = $app.DoScript($script, 1246973031) | ConvertFrom-Json
        $result.pages = $stats.pages
        $result.overset = $stats.overset
        $result.bad_fonts = $stats.bad_fonts
        $result.bad_links = $stats.bad_links
        $result.proof_status = 'visual_review_pending'
    }
} elseif ($job.format -eq 'docx') {
    $app = [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    if ($app.Documents.Count -ne 0) {
        $result.reason = 'user_documents_open'
    } else {
        $owned = $null
        $missing = [Type]::Missing
        try {
            $owned = $app.Documents.Open($job.input, $false, $true, $false, $missing, $missing, $false, $missing, $missing, $missing, $missing, $false)
            $owned.Repaginate()
            $result.pages = $owned.ComputeStatistics(2)
            $owned.ExportAsFixedFormat($job.output, 17, $false)
            $result.proof_status = 'visual_review_pending'
        } finally {
            if ($null -ne $owned) { $owned.Close(0) }
        }
    }
} else { throw 'Unsupported proof format' }
if ($result.proof_status -eq 'visual_review_pending') {
    if (-not (Test-Path -LiteralPath $job.output)) { throw 'Export did not produce a PDF' }
    $result.output = $job.output
    $result.output_hash = (Get-FileHash -LiteralPath $job.output -Algorithm SHA256).Hash.ToLowerInvariant()
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $job.result -Encoding UTF8
$result | ConvertTo-Json -Compress

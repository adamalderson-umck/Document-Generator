param([Parameter(Mandatory=$true)][string]$RequestPath,
      [Parameter(Mandatory=$true)][string]$ApprovedRoot)
$ErrorActionPreference = 'Stop'
$job = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
$config = Get-Content -LiteralPath $job.input -Raw | ConvertFrom-Json
$day = [datetime]::ParseExact($config.service_date, 'yyyy-MM-dd', $null)
if ($day.DayOfWeek -ne 'Sunday') { throw 'Expected Sunday' }
$lookback = [int]$config.lookback_days
$limit = [int]$config.max_messages_per_folder
if ($lookback -lt 1 -or $lookback -gt 45 -or $limit -lt 1 -or $limit -gt 2000) { throw 'Invalid collection bounds' }
if (-not $config.store_name -or @($config.folders).Count -eq 0) { throw 'Explicit store and folders required' }
$outlook = [Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application')
$namespace = $outlook.Session
$matches = @()
for ($i=1; $i -le $namespace.Stores.Count; $i++) {
    $candidate = $namespace.Stores.Item($i)
    if ($candidate.DisplayName -eq $config.store_name) { $matches += $candidate }
}
if ($matches.Count -ne 1) { throw 'Configured store unavailable or ambiguous; no PST will be mounted' }
$store = $matches[0]
$start = $day.AddDays(-$lookback)
$end = $day.AddDays(1)
$filter = "[ReceivedTime] >= '$($start.ToString('MM/dd/yyyy hh:mm tt'))' AND [ReceivedTime] < '$($end.ToString('MM/dd/yyyy hh:mm tt'))'"
$records = @()
$findings = @()
$attachmentRoot = Join-Path (Split-Path -Parent $job.output) ($job.id + '-attachments')
if (Test-Path -LiteralPath $attachmentRoot) { throw 'Attachment destination exists' }
New-Item -ItemType Directory -Path $attachmentRoot | Out-Null
foreach ($folderPath in $config.folders) {
    $folder = $store.GetRootFolder()
    foreach ($part in ($folderPath -split '\\')) { $folder = $folder.Folders.Item($part) }
    $items = $folder.Items.Restrict($filter)
    $items.Sort('[ReceivedTime]', $false)
    $count = [Math]::Min($items.Count, $limit)
    if ($items.Count -gt $limit) { $findings += "Collection truncated in $folderPath" }
    for ($i=1; $i -le $count; $i++) {
        if ([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($job.deadline)) { throw 'Collection deadline reached' }
        $item = $items.Item($i)
        if ([string]$item.MessageClass -notlike 'IPM.Note*') { continue }
        $attachments = @()
        for ($a=1; $a -le $item.Attachments.Count; $a++) {
            $attachment = $item.Attachments.Item($a)
            $saved = $null
            $hash = $null
            if ([IO.Path]::GetExtension([string]$attachment.FileName) -ieq '.docx') {
                if ($attachment.Size -gt 20971520) { throw 'DOCX attachment exceeds 20 MB bound' }
                $saved = Join-Path $attachmentRoot (([guid]::NewGuid().ToString('N')) + '.docx')
                $attachment.SaveAsFile($saved)
                $hash = (Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash.ToLowerInvariant()
            }
            $attachments += @{filename=[string]$attachment.FileName; size=$attachment.Size; saved_path=$saved; sha256=$hash}
        }
        $records += @{entry_id=[string]$item.EntryID; store_id=[string]$store.StoreID;
            folder=[string]$folderPath; message_class=[string]$item.MessageClass;
            received=([datetimeoffset]$item.ReceivedTime).ToString('o');
            modified=([datetimeoffset]$item.LastModificationTime).ToString('o');
            sender=[string]$item.SenderName; from=[string]$item.SenderEmailAddress;
            subject=[string]$item.Subject; body=[string]$item.Body; attachments=$attachments}
    }
}
$payload = @{service_date=$config.service_date; retrieved_at=[DateTimeOffset]::UtcNow.ToString('o');
    messages=$records; findings=$findings; completeness='not_assessed'; pst_auto_mounted=$false}
$temporary = $job.output + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
$payload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $temporary -Encoding UTF8
[IO.File]::Move($temporary, $job.output)

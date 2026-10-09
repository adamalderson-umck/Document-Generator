param(
  [Parameter(Mandatory=$true)]
  [string]$ServiceDate,

  [string]$StoreName = "Adam Alderson",
  [string]$PstPath = "C:\Users\kentu\AppData\Local\Microsoft\Outlook\Adam Alderson.pst",
  [string]$OutputRoot = "tmp/weekly_review_sources"
)

$ErrorActionPreference = "Stop"
$service = [datetime]::ParseExact($ServiceDate, "yyyy-MM-dd", $null)
$subjectMarker = $service.ToString("MMMM d", [Globalization.CultureInfo]::InvariantCulture) + " worship notes"
$outputDir = Join-Path $OutputRoot $service.ToString("yyyy-MM-dd")
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.Session
$pstAutoMounted = $false

function Get-OutlookStore($namespace, [string]$storeName, [string]$pstPath) {
  $resolvedPstPath = if ($pstPath) { [System.IO.Path]::GetFullPath($pstPath) } else { "" }
  for ($i = 1; $i -le $namespace.Stores.Count; $i++) {
    $candidate = $namespace.Stores.Item($i)
    $displayName = try { [string]$candidate.DisplayName } catch { "" }
    $filePath = try { [System.IO.Path]::GetFullPath([string]$candidate.FilePath) } catch { "" }
    if ($displayName -eq $storeName -or ($resolvedPstPath -and $filePath -eq $resolvedPstPath)) {
      return $candidate
    }
  }
  return $null
}

$store = Get-OutlookStore $ns $StoreName $PstPath
if (-not $store -and (Test-Path -LiteralPath $PstPath)) {
  # 2 is Outlook OlStoreType.olStoreUnicode.
  $ns.AddStoreEx($PstPath, 2)
  $pstAutoMounted = $true
  Start-Sleep -Milliseconds 500
  $store = Get-OutlookStore $ns $StoreName $PstPath
}

if (-not $store) {
  if (Test-Path -LiteralPath $PstPath) {
    throw "Outlook store not found after PST mount attempt: $StoreName at $PstPath"
  }
  throw "Outlook store not found and PST path does not exist: $StoreName at $PstPath"
}

function Find-Folder($folder, [string[]]$parts, [int]$idx) {
  if ($idx -ge $parts.Count) { return $folder }
  for ($i = 1; $i -le $folder.Folders.Count; $i++) {
    $child = $folder.Folders.Item($i)
    if ($child.Name -eq $parts[$idx]) {
      return Find-Folder $child $parts ($idx + 1)
    }
  }
  return $null
}

function Safe-Text([scriptblock]$block) {
  try {
    return [string](& $block)
  } catch {
    return ""
  }
}

function Message-Record($item, $folderPath) {
  [PSCustomObject]@{
    folder = $folderPath
    received = Safe-Text { ([datetime]$item.ReceivedTime).ToString("s") }
    sender = Safe-Text { $item.SenderName }
    "from" = Safe-Text { $item.SenderEmailAddress }
    subject = Safe-Text { $item.Subject }
    body = Safe-Text { $item.Body }
    attachments = @()
  }
}

$root = $store.GetRootFolder()
$nathan = Find-Folder $root @("Inbox", "Staff", "Nathan") 0
$music = Find-Folder $root @("Inbox", "Music") 0
if (-not $nathan) { throw "Nathan folder not found" }
if (-not $music) { throw "Music folder not found" }

$sourceMessages = @()
$nathanItems = $nathan.Items
$nathanItems.Sort("[ReceivedTime]", $true)
for ($i = 1; $i -le $nathanItems.Count; $i++) {
  $item = $nathanItems.Item($i)
  $subject = Safe-Text { $item.Subject }
  if ($subject -notlike "*$subjectMarker*") { continue }
  $record = Message-Record $item "Inbox\Staff\Nathan"
  $attachments = @()
  for ($a = 1; $a -le $item.Attachments.Count; $a++) {
    $att = $item.Attachments.Item($a)
    $savedPath = ""
    if ($att.FileName -like "*1030*.docx" -or $att.FileName -like "*10*30*.docx") {
      $savedPath = Join-Path $outputDir $att.FileName
      $att.SaveAsFile($savedPath)
    }
    $attachments += [PSCustomObject]@{
      filename = $att.FileName
      size = $att.Size
      saved_path = $savedPath
    }
  }
  $record.attachments = $attachments
  $sourceMessages += $record
}

$musicMessages = @()
$start = $service.AddDays(-6).Date
$end = $service.AddDays(1).Date
$filter = "[ReceivedTime] >= '$($start.ToString("MM/dd/yyyy hh:mm tt"))' AND [ReceivedTime] < '$($end.ToString("MM/dd/yyyy hh:mm tt"))'"
$musicItems = $music.Items
$musicItems.Sort("[ReceivedTime]", $true)
$restricted = $musicItems.Restrict($filter)
for ($i = 1; $i -le $restricted.Count; $i++) {
  $item = $restricted.Item($i)
  $messageClass = Safe-Text { $item.MessageClass }
  if ($messageClass -notlike "IPM.Note*") { continue }
  $musicMessages += Message-Record $item "Inbox\Music"
}

$payload = [PSCustomObject]@{
  service_date = $service.ToString("yyyy-MM-dd")
  subject_marker = $subjectMarker
  store_name = $StoreName
  pst_path = $PstPath
  pst_auto_mounted = $pstAutoMounted
  output_dir = (Resolve-Path $outputDir).Path
  source_messages = $sourceMessages
  music_messages = $musicMessages
}

$jsonPath = Join-Path $outputDir "sources.json"
$payload | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonPath
Write-Output $jsonPath

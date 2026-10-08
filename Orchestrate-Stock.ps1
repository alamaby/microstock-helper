<#
.SYNOPSIS
  Orkestrator microstock: dari image hasil generate AI sampai siap upload
  Adobe Stock + Dreamstime (jalur JPG/SVG/EPS).

.DESCRIPTION
  Tahapan (jalur JPG):
    0. Preflight  : cek ffmpeg, ExifTool, Upscayl, script pendamping, generator.
    1. Rename     : penomoran 001_... in-place by CreationTime (skip bila sudah).
    2. Convert    : non-JPG (png/webp) -> JPG kecil q:v 1 ke _stock/02_jpg_small.
    3. Upscale    : JPG kecil -> PNG 5x ke _stock/03_upscaled (via Upscayl).
    4. Final JPG  : PNG 5x -> JPG q:v 1 ke _stock/04_final_jpg.
    5. Metadata   : SELALU via inference API dari JPG KECIL (hemat),
                  backend lokal dinonaktifkan (terlalu lambat).
                  Hasil jadi 2 CSV Adobe+Dreamstime.
    6. Embed      : metadata -> for_adobe/ + for_dreamstime/ (file upload).

  Tahapan (jalur SVG / EPS - vektor dari raster, resume-aware):
    0. Preflight  : cek ffmpeg, ExifTool, vtracer, Inkscape, script
                  vektor, generator (tanpa Upscayl).
    1. Rename     : sama seperti JPG.
    2. Convert    : sama seperti JPG (JPG kecil = bahan trace + inference).
                  SKIP bila _stock/02_jpg_small sudah lengkap (mis. habis jalur JPG).
    3. Metadata   : reuse 2 CSV embed bila sudah lengkap dari run JPG
                  (tanpa API); rebuild dari metadata.csv mentah bila
                  Copyright/Creator berubah; generate API hanya bila kurang.
    4. Trace      : JPG kecil -> SVG ke _stock/05_svg (via vtracer,
                  color-cluster/cutout/spline). Yang sudah valid di-skip.
    5. Preview    : SVG -> JPG besar ke _stock/06_preview_jpg (render
                  Inkscape selebar PreviewWidth, lalu ffmpeg q:v 1).
                  Basename SAMA dengan SVG. Yang sudah ada di-skip.
    6. EPS        : (jalur EPS saja) SVG -> EPS ke _stock/07_eps
                  via Inkscape CLI. Paket EPS = .eps + .jpg saja.
    7. Embed      : metadata -> for_adobe_svg/for_dreamstime_svg atau
                  for_adobe_eps/for_dreamstime_eps (TERPISAH dari
                  for_adobe/for_dreamstime jalur JPG agar tidak menimpa)
                  berisi pasangan (JPG+SVG atau JPG+EPS, basename sama) +
                  salinan CSV agensi. JPG triple-sync, EPS XMP,
                  SVG injeksi XML native (best-effort).

.EXAMPLE
  .\Orchestrate-Stock.ps1
  .\Orchestrate-Stock.ps1 -SourceDir "D:\batch1" -Force
  .\Orchestrate-Stock.ps1 -SourceDir "D:\batch1","D:\batch2","D:\batch3" -Force
  (antrean banyak direktori, semua config default, jalan berurutan)
#>
[CmdletBinding()]
param(
  [ValidateSet("JPG", "SVG", "EPS")][string]$Target = "",
  [string[]]$SourceDir = @(),
  [ValidateRange(2, 5)][int]$Scale = 5,
  [ValidateRange(1000, 15000)][int]$PreviewWidth = 6000,
  [string]$Copyright = "alamaby",
  [string]$Creator = "alamaby",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$BinExif = "C:\Apps\exiftool\exiftool.exe"
$BinUpscayl = "C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe"
$BinVtracer = "C:\Apps\vtracer.exe"
$BinInkscape = "C:\Program Files\Inkscape\bin\inkscape.com"
$GenDir = Join-Path $PSScriptRoot "microstock-metadata-generator"
$Stopwords = @("a", "an", "the", "and", "or", "but", "of", "on", "in", "at", "to",
  "for", "from", "with", "without", "by", "as", "is", "are", "was", "were", "be",
  "been", "no", "not", "nor", "so", "than", "then", "too", "very", "can", "will",
  "just", "over", "under", "between", "into", "through", "during", "each", "other",
  "own", "same", "both", "few", "more", "most", "some", "only", "its", "it",
  "this", "that", "these", "those", "there", "their", "they", "them", "he",
  "she", "his", "her", "you", "your", "we", "our", "us", "who", "what", "when",
  "where", "which", "while", "about", "against", "above", "below", "up", "down",
  "out", "off", "again", "once", "all", "any")

$script:stages = @()
$script:swTotal = [System.Diagnostics.Stopwatch]::StartNew()
$script:MetadataBackend = "api"
# Tangkap param terikat di scope skrip (di dalam fungsi $PSBoundParameters milik fungsi itu).
$script:boundKeys = @($PSBoundParameters.Keys)

function Write-Stage($n, $title) {
  Write-Host ""
  Write-Host ("  ===== [TAHAP {0}] {1} =====" -f $n, $title) -ForegroundColor Cyan
}

function Add-Stage($n, $title, $status, $detail) {
  $script:stages += [pscustomobject]@{ No = $n; Tahap = $title; Status = $status; Detail = $detail }
}

function Write-FailedList([string]$ListPath, [string[]]$Items) {
  # Tulis daftar path gagal satu per baris (UTF8 tanpa BOM); buat folder induk.
  # Diam bila $Items kosong (tulis file kosong). Tidak throw.
  try {
    $parent = Split-Path $ListPath -Parent
    if ($parent -and (-not (Test-Path -LiteralPath $parent -PathType Container))) {
      New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    @($Items) | Out-File -FilePath $ListPath -Encoding UTF8 -NoClobber
    if (-not (Test-Path -LiteralPath $ListPath)) {
      [IO.File]::WriteAllLines($ListPath, @())
    }
  } catch {
    Write-Host ("  [!] Gagal menulis daftar gagal ke {0}: {1}" -f $ListPath, $_.Exception.Message) -ForegroundColor Yellow
  }
}

function Get-MissingBasenames([string]$InDir, [string]$OutDir, [string]$OutFilter = "*", [string]$InFilter = "*") {
  # Bandingkan basename (tanpa ekstensi) file input vs output; return array
  # nama input yang tidak punya pasangan output.
  # Pencocokan lintas-ekstensi via basename saja.
  try {
    if (-not (Test-Path -LiteralPath $InDir -PathType Container)) { return @() }
    if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) { return @() }
    $outNames = @{}
    foreach ($o in (Get-ChildItem -LiteralPath $OutDir -File -Filter $OutFilter -ErrorAction SilentlyContinue)) {
      $outNames[$o.BaseName.ToLower()] = $true
    }
    $miss = @()
    foreach ($i in (Get-ChildItem -LiteralPath $InDir -File -Filter $InFilter -ErrorAction SilentlyContinue)) {
      if (-not $outNames.ContainsKey($i.BaseName.ToLower())) { $miss += $i.FullName }
    }
    return $miss
  } catch {
    Write-Host ("  [!] Gagal menghitung missing basenames ({0} -> {1}): {2}" -f $InDir, $OutDir, $_.Exception.Message) -ForegroundColor Yellow
    return @()
  }
}

function Get-NormBase([string]$name) {
  # Normalisasi basename untuk perbandingan: ambil nama file (tanpa path),
  # kupas SATU ekstensi image/vektor yang dikenal bila ada, lowercase.
  # (GetFileNameWithoutExtension tidak cocok karena basename kita
  #  mengandung titik, mis. "001__001.-Create-...".)
  $f = [IO.Path]::GetFileName($name)
  foreach ($e in @(".jpg", ".jpeg", ".png", ".webp", ".svg", ".eps")) {
    if ($f.ToLower().EndsWith($e)) { return $f.Substring(0, $f.Length - $e.Length).ToLower() }
  }
  return $f.ToLower()
}

function Get-CsvSourceFile($row) {
  # Template resmi Adobe memakai header Filename; CSV lama memakai SourceFile.
  if ($row.Filename) { return $row.Filename }
  return $row.SourceFile
}

function Test-EmbedCsvComplete([string]$CsvPath, [string[]]$NeedBasenames) {
  # True bila CSV embed ada dan setiap basename di $NeedBasenames
  # punya baris (bandingkan via Get-NormBase atas kolom Filename/SourceFile).
  try {
    if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) { return $false }
    if ($NeedBasenames.Count -eq 0) { return $false }
    $have = @{}
    foreach ($r in (Import-Csv -LiteralPath $CsvPath -Encoding UTF8 -ErrorAction Stop)) {
      $sf = Get-CsvSourceFile $r
      if ($sf) {
        $have[(Get-NormBase $sf)] = $true
      }
    }
    foreach ($b in $NeedBasenames) {
      if (-not $have.ContainsKey((Get-NormBase $b))) { return $false }
    }
    return $true
  } catch { return $false }
}

function Test-GenCsvComplete([string]$GenCsv, [string[]]$NeedBasenames) {
  # True bila metadata.csv mentah ada dan setiap basename kebutuhan
  # ada di baris status success/skipped (kolom filename).
  try {
    if (-not (Test-Path -LiteralPath $GenCsv -PathType Leaf)) { return $false }
    if ($NeedBasenames.Count -eq 0) { return $false }
    $have = @{}
    foreach ($r in (Import-Csv -LiteralPath $GenCsv -Encoding UTF8 -ErrorAction Stop |
      Where-Object { $_.status -in @("success", "skipped") })) {
      if ($r.filename) {
        $have[(Get-NormBase $r.filename)] = $true
      }
    }
    foreach ($b in $NeedBasenames) {
      if (-not $have.ContainsKey((Get-NormBase $b))) { return $false }
    }
    return $true
  } catch { return $false }
}

function Test-EmbedCsvIdentity([string]$CsvPath, [string]$Copyright, [string]$Creator) {
  # True bila Copyright/Creator di CSV sama dengan yang diminta
  # (cek baris pertama; bila CSV kosong -> false agar di-rebuild).
  try {
    if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) { return $false }
    $first = Import-Csv -LiteralPath $CsvPath -Encoding UTF8 -ErrorAction Stop | Select-Object -First 1
    if (-not $first) { return $false }
    return ($first.Copyright -eq $Copyright -and $first.Creator -eq $Creator)
  } catch { return $false }
}

function Read-Folder($Prompt) {
  while ($true) {
    $v = (Read-Host $Prompt).Trim().Trim('"').Trim("'")
    if ($v -ne "" -and (Test-Path -LiteralPath $v -PathType Container)) {
      return (Get-Item -LiteralPath $v).FullName
    }
    Write-Host "  Folder tidak ditemukan, coba lagi." -ForegroundColor Red
  }
}

function Select-Option([string]$Title, [string[]]$Options, [int]$Default = 0) {
  # Menu panah: Up/Down + Enter (atau tekan 1/2). Non-interaktif -> default.
  if ([Console]::IsInputRedirected) { return $Options[$Default] }
  try {
    $sel = $Default
    Write-Host ("  {0} (panah Up/Down + Enter):" -f $Title) -ForegroundColor Gray
    $top = [Console]::CursorTop
    for ($i = 0; $i -lt $Options.Count; $i++) { Write-Host "" }
    while ($true) {
      [Console]::SetCursorPosition(0, $top)
      for ($i = 0; $i -lt $Options.Count; $i++) {
        if ($i -eq $sel) { Write-Host ("> {0}" -f $Options[$i]) -ForegroundColor Green }
        else { Write-Host ("  {0}" -f $Options[$i]) -ForegroundColor DarkGray }
      }
      $key = [Console]::ReadKey($true)
      if ($key.Key -eq "UpArrow") { $sel = ($sel - 1 + $Options.Count) % $Options.Count }
      elseif ($key.Key -eq "DownArrow") { $sel = ($sel + 1) % $Options.Count }
      elseif ($key.Key -eq "Enter") { break }
      elseif ($key.Key -eq "Escape") { $sel = $Default; break }
      elseif ($key.KeyChar -ge "1" -and $key.KeyChar -le "9") {
        $n = [int]$key.KeyChar.ToString() - 1
        if ($n -lt $Options.Count) { $sel = $n; break }
      }
    }
    [Console]::SetCursorPosition(0, $top)
    for ($i = 0; $i -lt $Options.Count; $i++) {
      if ($i -eq $sel) { Write-Host ("> {0}  <-- dipilih" -f $Options[$i]) -ForegroundColor Green }
      else { Write-Host ("  {0}" -f $Options[$i]) -ForegroundColor DarkGray }
    }
    return $Options[$sel]
  } catch {
    return $Options[$Default]
  }
}
function Ask-Default($Prompt, $Default) {
  $v = (Read-Host ("{0} [Enter={1}]" -f $Prompt, $Default)).Trim()
  if ([string]::IsNullOrWhiteSpace($v)) { return $Default }
  return $v
}

function Invoke-Child($File, [hashtable]$Arguments) {
  # Out-Host: tampilkan progres child apa adanya TANPA mencemari return value
  # (Write-Output child tertangkap assignment bila tidak di-host-kan).
  # Try-catch: tangani exception dari child (ErrorAction=Stop) agar orchestrator
  # tetap bisa memproses partial failure dengan konsisten.
  try {
    & $File @Arguments | Out-Host
    return $LASTEXITCODE
  } catch {
    Write-Host ("  [!] Child script {0} throw: {1}" -f (Split-Path $File -Leaf), $_.Exception.Message) -ForegroundColor Red
    if ($_.ScriptStackTrace) {
      $stackLines = @($_.ScriptStackTrace -split "`r?`n" | Where-Object { $_ -match '\S' } | Select-Object -First 5)
      Write-Host ("  [!] Stack: {0}" -f ($stackLines -join " <- ")) -ForegroundColor DarkGray
    }
    return -1
  }
}

# ---------- Adobe Stock category mapping ----------
# Generator mengeluarkan nama kategori (LOV 20 nilai di
# microstock-metadata-generator/.../constants.py, warisan taksonomi Fotolia).
# CSV Adobe memakai kolom Category terpisah; nilai diisi nama kategori portal
# resmi yang paling dekat ("closest one", sesuai artikel "Choose the right
# category for your content", helpx, Jun 2026). "Other" dikosongkan agar
# Sensei/portal mengusulkan sendiri daripada kategori yang salah.
# CATATAN: spec CSV resmi meminta NOMOR kategori (dari dialog upload-CSV
# portal), bukan nama. Kolom ini memakai NAMA agar bisa diverifikasi dari
# artikel; tukar ke nomor bila daftar nomor sudah dikonfirmasi dari portal.
$script:AdobeCategoryMap = @{
  "animals"                = "Animals"
  "architecture"           = "Buildings and architecture"
  "backgrounds and textures" = "Graphic resources"
  "beauty and fashion"     = "People"
  "business"               = "Business"
  "education"              = "People"
  "food and drink"         = "Food"
  "healthcare and medical" = "Science"
  "holidays"               = "Culture and religion"
  "industrial"             = "Industry"
  "nature"                 = "The environment"
  "people"                 = "People"
  "religion and culture"   = "Culture and religion"
  "science"                = "Science"
  "signs and symbols"      = "Graphic resources"
  "sports and fitness"     = "Sports"
  "technology"             = "Technology"
  "transportation"         = "Transport"
  "travel"                 = "Travel"
  "other"                  = ""
}

function Get-AdobeCategory([string]$GeneratorCategory) {
  # Nama kategori generator -> nama kategori portal Adobe terdekat.
  # Tak dikenal/kosong/"Other" -> "" (kolom dibiarkan kosong).
  $k = ([string]$GeneratorCategory).Trim().ToLower()
  if ([string]::IsNullOrWhiteSpace($k)) { return "" }
  if ($script:AdobeCategoryMap.ContainsKey($k)) { return $script:AdobeCategoryMap[$k] }
  return ""
}

function Test-EmbedCsvHasColumn([string]$CsvPath, [string]$Column) {
  # True bila file CSV ada dan punya kolom bernama $Column.
  try {
    if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) { return $false }
    $first = Import-Csv -LiteralPath $CsvPath -Encoding UTF8 -ErrorAction Stop | Select-Object -First 1
    if (-not $first) { return $false }
    return ($null -ne ($first.PSObject.Properties | Where-Object { $_.Name -ieq $Column } | Select-Object -First 1))
  } catch { return $false }
}

# ---------- Transform: generator CSV -> 2 CSV embed ----------
function ConvertTo-EmbedCsvs($GenCsv, $AdobeCsv, $DreamCsv, $Copyright, $Creator, [string[]]$OnlyBasenames = @()) {
  # Resume: baris "skipped" menyimpan metadata penuh (prior_items) dan
  # tetap layak embed - hanya baris gagal/nyata yang dikecualikan.
  # $OnlyBasenames (opsional): bila non-kosong, lewati baris yang basenamenya
  # tidak ada di daftar (case-insensitive, tanpa ekstensi).
  $allRows = Import-Csv $GenCsv -Encoding UTF8 | Where-Object { $_.status -in @("success", "skipped") }
  $failed = @(Import-Csv $GenCsv -Encoding UTF8 | Where-Object { $_.status -notin @("success", "skipped") }).Count
  $filteredOut = 0
  if ($OnlyBasenames.Count -gt 0) {
    $set = @{}
    foreach ($b in $OnlyBasenames) { $set[$b.ToLower()] = $true }
    $skipSet = @{}
    $rows = @()
    foreach ($r in $allRows) {
      $bn = ([IO.Path]::GetFileNameWithoutExtension($r.filename)).ToLower()
      if ($set.ContainsKey($bn)) { $rows += $r } else { $skipSet[$bn] = $true }
    }
    $filteredOut = $skipSet.Count
  } else {
    $rows = $allRows
  }
  $adobe = @(); $dream = @()
  foreach ($r in $rows) {
    $phrases = @($r.keywords -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique)
    if ($phrases.Count -gt 49) { $phrases = $phrases[0..48] }
    $title70 = if ($r.title.Length -gt 70) { $r.title.Substring(0, 70) } else { $r.title }
    $adobe += [pscustomobject]@{
      Filename    = $r.filename
      Title       = $title70
      Description = $r.description
      Keywords    = ($phrases -join ", ")
      Category    = (Get-AdobeCategory $r.category)
      Releases    = ""
      Copyright   = $Copyright
      Creator     = $Creator
    }
    $words = @()
    foreach ($p in $phrases) {
      foreach ($w in ($p.ToLower() -split "[^a-z0-9]+")) {
        if ($w.Length -ge 2 -and $Stopwords -notcontains $w -and $words -notcontains $w) { $words += $w }
      }
    }
    if ($words.Count -gt 70) { $words = $words[0..69] }
    $title200 = if ($r.title.Length -gt 200) { $r.title.Substring(0, 200) } else { $r.title }
    $dream += [pscustomobject]@{
      SourceFile  = $r.filename
      Title       = $title200
      Description = $r.description
      Keywords    = ($words -join ", ")
      Copyright   = $Copyright
      Creator     = $Creator
    }
  }
  $cols = @("SourceFile", "Title", "Description", "Keywords", "Copyright", "Creator")
  $adobeCols = @("Filename", "Title", "Description", "Keywords", "Category", "Releases", "Copyright", "Creator")
  $adobe | Select-Object $adobeCols | Export-Csv $AdobeCsv -Encoding UTF8 -NoTypeInformation
  $dream | Select-Object $cols | Export-Csv $DreamCsv -Encoding UTF8 -NoTypeInformation
  return [pscustomobject]@{ OK = $rows.Count; Failed = $failed; FilteredOut = $filteredOut }
}

function Get-ImageExtByMagic([string]$path) {
  try {
    $fs = [IO.File]::OpenRead($path); $mg = New-Object byte[] 12
    $n = $fs.Read($mg, 0, 12); $fs.Close()
    if ($n -ge 2 -and $mg[0] -eq 0xFF -and $mg[1] -eq 0xD8) { return ".jpg" }
    if ($n -ge 4 -and $mg[0] -eq 0x89 -and $mg[1] -eq 0x50 -and $mg[2] -eq 0x4E -and $mg[3] -eq 0x47) { return ".png" }
    if ($n -ge 12 -and $mg[0] -eq 0x52 -and $mg[1] -eq 0x49 -and $mg[2] -eq 0x46 -and $mg[3] -eq 0x46 -and
        $mg[8] -eq 0x57 -and $mg[9] -eq 0x45 -and $mg[10] -eq 0x42 -and $mg[11] -eq 0x50) { return ".webp" }
  } catch { }
  return ""
}

function Restore-OrphanTmps([string]$dir) {
  # Pulihkan sisa interupsi rename fase-1 (*.renametmp yatim): kembalikan
  # ekstensi via magic bytes agar ikut penomoran normal. Return jumlah pulih.
  $n = 0
  foreach ($o in (Get-ChildItem -LiteralPath $dir -File -Filter "*.renametmp" -ErrorAction SilentlyContinue)) {
    $ext = Get-ImageExtByMagic $o.FullName
    if ($ext) {
      $rn = Join-Path $dir ("recovered_" + [Guid]::NewGuid().ToString("N") + $ext)
      Move-Item -LiteralPath $o.FullName -Destination $rn -Force
      Write-Host ("  Pulihkan yatim -> {0}" -f (Split-Path $rn -Leaf)) -ForegroundColor Yellow
      $n++
    } else {
      Write-Host ("  [!] yatim tak dikenal, dilewati: {0}" -f $o.Name) -ForegroundColor Yellow
    }
  }
  return $n
}

function Process-Dir($DirInput, $Idx, $Total) {
  # Proses SATU direktori (dipanggil berurutan untuk antrean batch).
  $SourceDir = (Get-Item -LiteralPath $DirInput.Trim().Trim('"').Trim("'")).FullName
  $script:stages = @()
  $script:swTotal.Restart()
  Write-Host ""
  Write-Host ("  ########## DIREKTORI [{0}/{1}]: {2} ##########" -f $Idx, $Total, $SourceDir) -ForegroundColor Magenta

  $stock = Join-Path $SourceDir "_stock"
  $small = Join-Path $stock "02_jpg_small"
  $up = Join-Path $stock "03_upscaled"
  $final = Join-Path $stock "04_final_jpg"
  $svgDir = Join-Path $stock "05_svg"
  $prevDir = Join-Path $stock "06_preview_jpg"
  $epsDir = Join-Path $stock "07_eps"
  $metaDir = Join-Path $stock "metadata"
  $rawDir = Join-Path $metaDir "raw"
  # Paket upload JPG tetap di for_adobe/for_dreamstime. Paket vektor
  # dipisah agar tidak menimpa hasil JPG: for_adobe_svg / for_adobe_eps.
  $forAdobeJpg = Join-Path $stock "for_adobe"
  $forDreamJpg = Join-Path $stock "for_dreamstime"
  $forAdobe = $forAdobeJpg
  $forDream = $forDreamJpg
  if ($Target -eq "SVG") {
    $forAdobe = Join-Path $stock "for_adobe_svg"
    $forDream = Join-Path $stock "for_dreamstime_svg"
  } elseif ($Target -eq "EPS") {
    $forAdobe = Join-Path $stock "for_adobe_eps"
    $forDream = Join-Path $stock "for_dreamstime_eps"
  }
  foreach ($d in @($stock, $small, $up, $final, $svgDir, $prevDir, $epsDir, $metaDir, $rawDir, $forAdobeJpg, $forDreamJpg, $forAdobe, $forDream)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
  }
  Start-Transcript -Path (Join-Path $stock "orchestrator.log") -Append | Out-Null

  try {
    Write-Host ""
    $logo = @(
      "   ___  ____   ____ _   _ _____ ____ _____ ____      _ _____ ___  ____  ",
      "  / _ \|  _ \ / ___| | | | ____/ ___|_   _|  _ \    / |_   _/ _ \|  _ \ ",
      " | | | | |_) | |   | |_| |  _| \___ \ | | | |_) |   | | | || | | | |_) |",
      " | |_| |  _ <| |___|  _  | |___ ___) || | |  _ <  __| | | || |_| |  _ < ",
      "  \___/|_| \_\\____|_| |_|_____|____/ |_| |_| \_\|___/  |_| \___/|_| \_\"
    )
    foreach ($l in $logo) { Write-Host $l -ForegroundColor Cyan }
    foreach ($l in $logo) { Write-Host ("    " + $l.TrimEnd()) -ForegroundColor DarkGray }
    Write-Host "   AI image -> siap upload Adobe + Dreamstime (Target: $Target)" -ForegroundColor Yellow
    Write-Host "  Sumber : $SourceDir" -ForegroundColor Gray
    Write-Host "  Kerja  : $stock" -ForegroundColor Gray
    if ($Target -in @("SVG", "EPS")) {
      $rsSmall = @(Get-ChildItem -LiteralPath $small -File -Filter "*.jpg" -ErrorAction SilentlyContinue).Count
      $rsFinal = @(Get-ChildItem -LiteralPath $final -File -Filter "*.jpg" -ErrorAction SilentlyContinue).Count
      $rsSvg = @(Get-ChildItem -LiteralPath $svgDir -File -Filter "*.svg" -ErrorAction SilentlyContinue).Count
      $rsPrev = @(Get-ChildItem -LiteralPath $prevDir -File -Filter "*.jpg" -ErrorAction SilentlyContinue).Count
      $rsEps = @(Get-ChildItem -LiteralPath $epsDir -File -Filter "*.eps" -ErrorAction SilentlyContinue).Count
      $batchProbe = (Get-Item -LiteralPath $SourceDir).Name -replace "[^\w\-]+", "_"
      $rsMetaA = Test-Path -LiteralPath (Join-Path $metaDir ($batchProbe + "_metadata_adobe.csv"))
      $rsMetaD = Test-Path -LiteralPath (Join-Path $metaDir ($batchProbe + "_metadata_dreamstime.csv"))
      $rsJpgDone = ($rsSmall -gt 0 -and $rsFinal -gt 0 -and $rsMetaA -and $rsMetaD)
      $rsJpgTag = if ($rsJpgDone) { "DONE (jalur JPG selesai, lanjutkan sisa task saja)" } else { "BELUM (jalur JPG belum lengkap, tahap 2-3 ikut jalan)" }
      Write-Host ("  Resume : JPG kecil={0}, JPG final={1}, metadata Adobe={2}, Dreamstime={3} -> {4}" -f $rsSmall, $rsFinal, $rsMetaA, $rsMetaD, $rsJpgTag) -ForegroundColor Yellow
      Write-Host ("  Resume : SVG={0}, preview={1}, EPS={2} (yang sudah valid di-skip, hanya yang belum diproses)." -f $rsSvg, $rsPrev, $rsEps) -ForegroundColor Yellow
      Write-Host ("  Upload : Adobe -> {0}" -f $forAdobe) -ForegroundColor Gray
      Write-Host ("  Upload : Dreamstime -> {0} (paket vektor terpisah, JPG lama tidak ditimpa)." -f $forDream) -ForegroundColor Gray
    }

    $imgExt = @(".png", ".jpg", ".jpeg", ".webp")

    # ---------- TAHAP 0: preflight ----------
    Write-Stage 0 "Preflight (Target $Target)"
    $fatal = @()
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { $fatal += "ffmpeg tidak di PATH" }
    if (-not (Test-Path -LiteralPath $BinExif -PathType Leaf)) { $fatal += "ExifTool tidak ada: $BinExif" }
    if ($Target -eq "JPG") {
      if (-not (Test-Path -LiteralPath $BinUpscayl -PathType Leaf)) { $fatal += "upscayl-bin.exe tidak ada: $BinUpscayl" }
      $need = @("Rename-Numbered.ps1", "Convert-PngToJpg.ps1", "Convert-WebpToJpg.ps1", "Upscale.ps1", "Embed-JpgMetadata.ps1")
    } else {
      if (-not (Test-Path -LiteralPath $BinVtracer -PathType Leaf)) { $fatal += "vtracer.exe tidak ada: $BinVtracer" }
      if (-not (Test-Path -LiteralPath $BinInkscape -PathType Leaf)) { $fatal += "inkscape.com tidak ada: $BinInkscape" }
      $need = @("Convert-PngToJpg.ps1", "Convert-WebpToJpg.ps1", "Trace-Svg.ps1", "Export-VectorPreview.ps1", "Embed-VectorMetadata.ps1")
      if ($Target -eq "EPS") { $need += "Convert-SvgToEps.ps1" }
    }
    foreach ($n in $need) { if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $n) -PathType Leaf)) { $fatal += "script pendamping hilang: $n" } }
    if (-not (Test-Path -LiteralPath (Join-Path $GenDir ".venv\Scripts\python.exe"))) {
      $fatal += "generator venv tidak ada - jalankan setup.bat di microstock-metadata-generator dulu"
    }
    # Backend dikunci API: key wajib ada, tanpa opsi lokal lagi.
    $envKey = [string]$env:MICROSTOCK_API_KEY
    $dotA = Join-Path (Get-Location) ".env"; $dotB = Join-Path $GenDir ".env"
    $hasKey = (-not [string]::IsNullOrWhiteSpace($envKey))
    foreach ($df in @($dotA, $dotB)) {
      if (Test-Path -LiteralPath $df) {
        $hit = @(Select-String -LiteralPath $df -Pattern "^\s*MICROSTOCK_API_KEY\s*=\s*\S" -ErrorAction SilentlyContinue).Count
        if ($hit -gt 0) { $hasKey = $true }
      }
    }
    if (-not $hasKey) { $fatal += "MICROSTOCK_API_KEY kosong - isi .env generator (copy .env.example)" }
    if ($fatal.Count -gt 0) {
      $fatal | ForEach-Object { Write-Host "  [X] $_" -ForegroundColor Red }
      Add-Stage 0 "Preflight" "GAGAL" ($fatal -join "; ")
      throw "Preflight gagal."
    }
    Write-Host "  [OK] semua prasyarat terpenuhi (backend metadata: $($script:MetadataBackend))." -ForegroundColor Green
    Add-Stage 0 "Preflight" "OK" "backend=$($script:MetadataBackend)"

    # ---------- TAHAP 1: rename ----------
    Write-Stage 1 "Rename 001_... (in-place)"
    $restored = Restore-OrphanTmps $SourceDir
    $imgs = @(Get-ChildItem -LiteralPath $SourceDir -File |
      Where-Object { $imgExt -contains $_.Extension.ToLower() } |
      Sort-Object CreationTime, Name)
    if ($imgs.Count -eq 0) { throw "Tidak ada image (png/jpg/webp) di $SourceDir." }
    $unnumbered = @($imgs | Where-Object { $_.Name -notmatch "^\d{3}_" })
    if ($unnumbered.Count -eq 0) {
      Write-Host ("  Semua {0} file sudah bernomor, skip rename." -f $imgs.Count) -ForegroundColor Green
      Add-Stage 1 "Rename" "SKIP" "$($imgs.Count) file sudah 001_..."
    } else {
      $plan = @()
      for ($i = 0; $i -lt $imgs.Count; $i++) {
        $base = $imgs[$i].Name -replace "^\d{3}_", ""
        $plan += [pscustomobject]@{ Full = $imgs[$i].FullName; Old = $imgs[$i].Name; New = ("{0:D3}_{1}" -f ($i + 1), $base) }
      }
      $dupes = @($plan.New | Group-Object | Where-Object { $_.Count -gt 1 })
      if ($dupes.Count -gt 0) { throw ("Nama tujuan duplikat: " + (($dupes | ForEach-Object { $_.Name }) -join ", ")) }
      $tmp = @()
      foreach ($p in $plan) {
        $t = Join-Path $SourceDir ([Guid]::NewGuid().ToString("N") + ".renametmp")
        Move-Item -LiteralPath $p.Full -Destination $t -Force
        $tmp += [pscustomobject]@{ Tmp = $t; New = $p.New; Old = $p.Old }
      }
      $ok = 0
      foreach ($t in $tmp) {
        Move-Item -LiteralPath $t.Tmp -Destination (Join-Path $SourceDir $t.New) -Force
        $ok++
      }
      Write-Host ("  Rename: {0} file (tertua = 001)." -f $ok) -ForegroundColor Green
      Add-Stage 1 "Rename" "OK" "$ok file"
      $imgs = @(Get-ChildItem -LiteralPath $SourceDir -File |
        Where-Object { $imgExt -contains $_.Extension.ToLower() } | Sort-Object CreationTime, Name)
    }

    # ---------- TAHAP 2: convert kecil ----------
    Write-Stage 2 "Convert ke JPG kecil"
    $nSmallPre = @(Get-ChildItem -LiteralPath $small -File -Filter "*.jpg" -ErrorAction SilentlyContinue).Count
    $missPre2 = @()
    if (-not $Force) { $missPre2 = Get-MissingBasenames $SourceDir $small "*.jpg" "*.*" }
    if ((-not $Force) -and $nSmallPre -gt 0 -and $missPre2.Count -eq 0) {
      Write-Host ("  JPG kecil sudah lengkap: {0} file, skip convert." -f $nSmallPre) -ForegroundColor Green
      Add-Stage 2 "Convert kecil" "SKIP" "$nSmallPre file sudah ada"
      $nSmall = $nSmallPre
    } else {
      if ((-not $Force) -and $missPre2.Count -gt 0) {
        Write-Host ("  JPG kecil: {0} sudah ada, {1} belum -> hanya yang belum diproses." -f $nSmallPre, $missPre2.Count) -ForegroundColor Yellow
      }
      $conv = @{ SourceDir = $SourceDir; OutDir = $small }
      if ($Force) { $conv.Force = $true }
      $partial2 = @()
      $codeWebp = Invoke-Child (Join-Path $PSScriptRoot "Convert-WebpToJpg.ps1") $conv
      if ($codeWebp -ne 0) { $partial2 += "WEBP" }
      $codePng = Invoke-Child (Join-Path $PSScriptRoot "Convert-PngToJpg.ps1") $conv
      if ($codePng -ne 0) { $partial2 += "PNG" }
      $copied = 0
      foreach ($f in ($imgs | Where-Object { $_.Extension -match "^\.jpe?g$" })) {
        $dst = Join-Path $small $f.Name
        if ((-not (Test-Path -LiteralPath $dst)) -or $Force) {
          $tmpC = "$dst.tmp"
          Copy-Item -LiteralPath $f.FullName -Destination $tmpC -Force
          Move-Item -LiteralPath $tmpC -Destination $dst -Force
          $copied++
        }
      }
      $nSmall = @(Get-ChildItem -LiteralPath $small -File -Filter "*.jpg").Count
      Write-Host ("  JPG kecil: {0} file (convert+copy)." -f $nSmall) -ForegroundColor Green
      if ($nSmall -eq 0) { throw "Tidak ada JPG kecil yang dihasilkan." }
      if ($nSmall -gt 0 -and $partial2.Count -gt 0) {
        $miss2 = Get-MissingBasenames $SourceDir $small "*.jpg" "*.*"
        if ($miss2.Count -gt 0) {
          Write-Host ("  [!] Convert kecil sebagian gagal (WEBP exit {0}, PNG exit {1}), lanjut dengan file sukses." -f $codeWebp, $codePng) -ForegroundColor Yellow
          Write-FailedList (Join-Path $stock "failed_02_convert-kecil.txt") $miss2
          Add-Stage 2 "Convert kecil" "PARTIAL" "$nSmall file, gagal: $($partial2 -join '+')"
        } else {
          Add-Stage 2 "Convert kecil" "OK" "$nSmall file"
        }
      } else {
        Add-Stage 2 "Convert kecil" "OK" "$nSmall file"
      }
    }

    if ($Target -eq "JPG") {
    # ---------- TAHAP 3: upscale ----------
    Write-Stage 3 ("Upscale {0}x" -f $Scale)
    $uargs = @{ InputDir = $small; OutputDir = $up; Scale = $Scale }
    if ($Force) { $uargs.Force = $true }
    $partial3 = @()
    $code = Invoke-Child (Join-Path $PSScriptRoot "Upscale.ps1") $uargs
    if ($code -ne 0) { $partial3 += "Upscale" }
    # Output Upscayl bernama *.jpg tapi isinya PNG -> betulkan ekstensi ke .png
    $fixed = 0
    foreach ($f in (Get-ChildItem -LiteralPath $up -File)) {
      if ($f.Extension -ieq ".jpg") {
        Move-Item -LiteralPath $f.FullName -Destination (Join-Path $up ($f.BaseName + ".png")) -Force
        $fixed++
      }
    }
    $nUp = @(Get-ChildItem -LiteralPath $up -File).Count
    Write-Host ("  Upscaled: {0} file (ekstensi dibetulkan: {1})." -f $nUp, $fixed) -ForegroundColor Green
    if ($nUp -eq 0) { throw "Upscale tidak menghasilkan file." }
    if ($nUp -gt 0 -and $partial3.Count -gt 0) {
      $miss3 = Get-MissingBasenames $small $up "*.*" "*.jpg"
      if ($miss3.Count -gt 0) {
        Write-Host ("  [!] Upscale sebagian gagal (exit {0}), lanjut dengan file sukses." -f $code) -ForegroundColor Yellow
        Write-FailedList (Join-Path $stock "failed_03_upscale.txt") $miss3
        Add-Stage 3 "Upscale" "PARTIAL" "$nUp file, gagal: $($partial3 -join '+')"
      } else {
        Add-Stage 3 "Upscale" "OK" "$nUp file"
      }
    } else {
      Add-Stage 3 "Upscale" "OK" "$nUp file"
    }

    # ---------- TAHAP 4: JPG final ----------
    Write-Stage 4 "Convert JPG final"
    $fin = @{ SourceDir = $up; OutDir = $final }
    if ($Force) { $fin.Force = $true }
    $partial4 = @()
    $code = Invoke-Child (Join-Path $PSScriptRoot "Convert-PngToJpg.ps1") $fin
    if ($code -ne 0) { $partial4 += "Convert" }
    $nFinal = @(Get-ChildItem -LiteralPath $final -File -Filter "*.jpg").Count
    Write-Host ("  JPG final: {0} file." -f $nFinal) -ForegroundColor Green
    if ($nFinal -eq 0) { throw "Tidak ada JPG final." }
    if ($nFinal -gt 0 -and $partial4.Count -gt 0) {
      $miss4 = Get-MissingBasenames $up $final "*.jpg" "*.*"
      if ($miss4.Count -gt 0) {
        Write-Host ("  [!] Convert JPG final sebagian gagal (exit {0}), lanjut dengan file sukses." -f $code) -ForegroundColor Yellow
        Write-FailedList (Join-Path $stock "failed_04_final-jpg.txt") $miss4
        Add-Stage 4 "JPG final" "PARTIAL" "$nFinal file (+$($partial4.Count) gagal, lihat failed_04_final-jpg.txt)"
      } else {
        Add-Stage 4 "JPG final" "OK" "$nFinal file"
      }
    } else {
      Add-Stage 4 "JPG final" "OK" "$nFinal file"
    }

    # ---------- TAHAP 5: metadata (dari JPG kecil) ----------
    Write-Stage 5 "Generate metadata (dari JPG kecil)"
    $runBat = Join-Path $GenDir "run.bat"
    $genCmd = "`"$runBat`" generate `"$small`" --output-dir `"$rawDir`" --backend $($script:MetadataBackend)"
    Write-Host ("  > {0}" -f $genCmd) -ForegroundColor DarkGray
    cmd /c $genCmd
    if ($LASTEXITCODE -ne 0) { throw "Generate metadata gagal (exit $LASTEXITCODE) - lihat $rawDir\processing.log." }
    $genCsv = Join-Path $rawDir "metadata.csv"
    if (-not (Test-Path -LiteralPath $genCsv)) { throw "metadata.csv tidak ditemukan di $rawDir." }
    $batch = (Get-Item -LiteralPath $SourceDir).Name -replace "[^\w\-]+", "_"
    $adobeCsv = Join-Path $metaDir ($batch + "_metadata_adobe.csv")
    $dreamCsv = Join-Path $metaDir ($batch + "_metadata_dreamstime.csv")
    $haveFinal = @(Get-ChildItem -LiteralPath $final -File -Filter "*.jpg" -ErrorAction SilentlyContinue | % { $_.BaseName })
    $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $Copyright $Creator $haveFinal
    Write-Host ("  Metadata: {0} OK, {1} gagal, {2} tanpa file-output (dilewati) -> {3}" -f $m.OK, $m.Failed, $m.FilteredOut, $metaDir) -ForegroundColor Green
    Add-Stage 5 "Metadata" "OK" "$($m.OK) OK, $($m.Failed) gagal"
    if ($m.OK -eq 0) { throw "Tidak ada metadata sukses untuk di-embed." }

    # ---------- TAHAP 6: embed ----------
    Write-Stage 6 "Embed metadata (Adobe + Dreamstime)"
    $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-JpgMetadata.ps1") @{ CsvPath = $adobeCsv; JpgDir = $final; OutDir = $forAdobe }
    if ($code -ne 0) { Write-Host "  [!] Embed Adobe sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-JpgMetadata.ps1") @{ CsvPath = $dreamCsv; JpgDir = $final; OutDir = $forDream }
    if ($code -ne 0) { Write-Host "  [!] Embed Dreamstime sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
    $nA = @(Get-ChildItem -LiteralPath $forAdobe -File -Filter "*.jpg").Count
    $nD = @(Get-ChildItem -LiteralPath $forDream -File -Filter "*.jpg").Count
    Write-Host ("  Siap upload: Adobe={0}, Dreamstime={1}." -f $nA, $nD) -ForegroundColor Green
    Add-Stage 6 "Embed" "OK" "Adobe=$nA, Dreamstime=$nD"
    } else {
    # ---------- TAHAP 3V: metadata vektor (dari JPG kecil, resume-aware) ----------
    # Bila direktori sudah menyelesaikan jalur JPG, metadata.csv + 2 CSV embed
    # sudah ada -> pakai ulang tanpa panggil API. 3 tier:
    #  Tier 1 full-reuse (tanpa API, tanpa rebuild),
    #  Tier 2 rebuild dari metadata.csv mentah (tanpa API),
    #  Tier 3 generate API penuh (baru atau belum lengkap).
    Write-Stage 3 "Generate metadata (dari JPG kecil)"
    $batch = (Get-Item -LiteralPath $SourceDir).Name -replace "[^\w\-]+", "_"
    $adobeCsv = Join-Path $metaDir ($batch + "_metadata_adobe.csv")
    $dreamCsv = Join-Path $metaDir ($batch + "_metadata_dreamstime.csv")
    $genCsv = Join-Path $rawDir "metadata.csv"
    $haveSmall = @(Get-ChildItem -LiteralPath $small -File -Filter "*.jpg" -ErrorAction SilentlyContinue | ForEach-Object { $_.BaseName })
    $reuseFull = ((-not $Force) -and
      (Test-EmbedCsvComplete $adobeCsv $haveSmall) -and
      (Test-EmbedCsvComplete $dreamCsv $haveSmall) -and
      (Test-EmbedCsvIdentity $adobeCsv $Copyright $Creator) -and
      (Test-EmbedCsvIdentity $dreamCsv $Copyright $Creator) -and
      (Test-EmbedCsvHasColumn $adobeCsv "Category"))
    if ($reuseFull) {
      $nReuse = @(Import-Csv -LiteralPath $adobeCsv -Encoding UTF8).Count
      Write-Host ("  Metadata sudah lengkap ({0} baris), reuse tanpa API -> {1}" -f $nReuse, $metaDir) -ForegroundColor Green
      Add-Stage 3 "Metadata" "SKIP" "$nReuse baris reuse (jalur JPG selesai)"
      $m = [pscustomobject]@{ OK = $nReuse; Failed = 0; FilteredOut = 0 }
    } else {
      $genComplete = ((-not $Force) -and (Test-GenCsvComplete $genCsv $haveSmall))
      if ($genComplete) {
        Write-Host "  metadata.csv mentah sudah lengkap, rebuild 2 CSV embed tanpa API." -ForegroundColor Yellow
      } else {
        $runBat = Join-Path $GenDir "run.bat"
        $genCmd = "`"$runBat`" generate `"$small`" --output-dir `"$rawDir`" --backend $($script:MetadataBackend)"
        Write-Host ("  > {0}" -f $genCmd) -ForegroundColor DarkGray
        cmd /c $genCmd
        if ($LASTEXITCODE -ne 0) { throw "Generate metadata gagal (exit $LASTEXITCODE) - lihat $rawDir\processing.log." }
        if (-not (Test-Path -LiteralPath $genCsv)) { throw "metadata.csv tidak ditemukan di $rawDir." }
      }
      $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $Copyright $Creator $haveSmall
      Write-Host ("  Metadata: {0} OK, {1} gagal, {2} tanpa file-output (dilewati) -> {3}" -f $m.OK, $m.Failed, $m.FilteredOut, $metaDir) -ForegroundColor Green
      Add-Stage 3 "Metadata" "OK" "$($m.OK) OK, $($m.Failed) gagal"
      if ($m.OK -eq 0) { throw "Tidak ada metadata sukses untuk di-embed." }
    }

    # ---------- TAHAP 4V: trace ----------
    Write-Stage 4 "Trace JPG kecil -> SVG (vtracer)"
    $missPre4v = @(Get-MissingBasenames $small $svgDir "*.svg" "*.jpg")
    $nSvgPre = @(Get-ChildItem -LiteralPath $svgDir -File -Filter "*.svg" -ErrorAction SilentlyContinue).Count
    if ((-not $Force) -and $missPre4v.Count -gt 0 -and $nSvgPre -gt 0) {
      Write-Host ("  SVG sudah ada {0}, kurang {1} -> hanya yang belum di-trace." -f $nSvgPre, $missPre4v.Count) -ForegroundColor Yellow
    }
    $targs = @{ InputDir = $small; OutDir = $svgDir }
    if ($Force) { $targs.Force = $true }
    $partial4v = @()
    $code = Invoke-Child (Join-Path $PSScriptRoot "Trace-Svg.ps1") $targs
    if ($code -ne 0) { $partial4v += "Trace" }
    $nSvg = @(Get-ChildItem -LiteralPath $svgDir -File -Filter "*.svg").Count
    Write-Host ("  SVG: {0} file." -f $nSvg) -ForegroundColor Green
    if ($nSvg -eq 0) { throw "Trace tidak menghasilkan SVG." }
    if ($nSvg -gt 0 -and $partial4v.Count -gt 0) {
      $miss4v = Get-MissingBasenames $small $svgDir "*.svg" "*.jpg"
      if ($miss4v.Count -gt 0) {
        Write-Host ("  [!] Trace SVG sebagian gagal (exit {0}), lanjut dengan file sukses." -f $code) -ForegroundColor Yellow
        Write-FailedList (Join-Path $stock "failed_04_trace-svg.txt") $miss4v
        Add-Stage 4 "Trace SVG" "PARTIAL" "$nSvg file, gagal: $($partial4v -join '+')"
      } else {
        Add-Stage 4 "Trace SVG" "OK" "$nSvg file"
      }
    } else {
      Add-Stage 4 "Trace SVG" "OK" "$nSvg file"
    }

    # ---------- TAHAP 5V: preview JPG besar ----------
    Write-Stage 5 ("Render preview JPG (lebar {0}px)" -f $PreviewWidth)
    $missPre5v = @(Get-MissingBasenames $svgDir $prevDir "*.jpg" "*.svg")
    $nPrevPre = @(Get-ChildItem -LiteralPath $prevDir -File -Filter "*.jpg" -ErrorAction SilentlyContinue).Count
    if ((-not $Force) -and $missPre5v.Count -gt 0 -and $nPrevPre -gt 0) {
      Write-Host ("  Preview sudah ada {0}, kurang {1} -> hanya yang belum di-render." -f $nPrevPre, $missPre5v.Count) -ForegroundColor Yellow
    }
    $pargs = @{ SvgDir = $svgDir; OutDir = $prevDir; Width = $PreviewWidth }
    if ($Force) { $pargs.Force = $true }
    $partial5v = @()
    $code = Invoke-Child (Join-Path $PSScriptRoot "Export-VectorPreview.ps1") $pargs
    if ($code -ne 0) { $partial5v += "Preview" }
    $nPrev = @(Get-ChildItem -LiteralPath $prevDir -File -Filter "*.jpg").Count
    Write-Host ("  Preview: {0} file." -f $nPrev) -ForegroundColor Green
    if ($nPrev -eq 0) { throw "Tidak ada JPG preview." }
    if ($nPrev -gt 0 -and $partial5v.Count -gt 0) {
      $miss5v = Get-MissingBasenames $svgDir $prevDir "*.jpg" "*.svg"
      if ($miss5v.Count -gt 0) {
        Write-Host ("  [!] Render preview JPG sebagian gagal (exit {0}), lanjut dengan file sukses." -f $code) -ForegroundColor Yellow
        Write-FailedList (Join-Path $stock "failed_05_preview-jpg.txt") $miss5v
        Add-Stage 5 "Preview JPG" "PARTIAL" "$nPrev file, gagal: $($partial5v -join '+')"
      } else {
        Add-Stage 5 "Preview JPG" "OK" "$nPrev file"
      }
    } else {
      Add-Stage 5 "Preview JPG" "OK" "$nPrev file"
    }

    # ---------- TAHAP 6V: EPS (jalur EPS saja; paket = .eps + .jpg) ----------
    $vecSrc = $svgDir; $vecKind = "svg"; $vecFilter = "*.svg"
    if ($Target -eq "EPS") {
      Write-Stage 6 "Convert SVG -> EPS (Inkscape)"
      $missPre6v = @(Get-MissingBasenames $svgDir $epsDir "*.eps" "*.svg")
      $nEpsPre = @(Get-ChildItem -LiteralPath $epsDir -File -Filter "*.eps" -ErrorAction SilentlyContinue).Count
      if ((-not $Force) -and $missPre6v.Count -gt 0 -and $nEpsPre -gt 0) {
        Write-Host ("  EPS sudah ada {0}, kurang {1} -> hanya yang belum di-convert." -f $nEpsPre, $missPre6v.Count) -ForegroundColor Yellow
      }
      $eargs = @{ SvgDir = $svgDir; OutDir = $epsDir }
      if ($Force) { $eargs.Force = $true }
      $partial6v = @()
      $code = Invoke-Child (Join-Path $PSScriptRoot "Convert-SvgToEps.ps1") $eargs
      if ($code -ne 0) { $partial6v += "EPS" }
      $nEps = @(Get-ChildItem -LiteralPath $epsDir -File -Filter "*.eps").Count
      Write-Host ("  EPS: {0} file." -f $nEps) -ForegroundColor Green
      if ($nEps -eq 0) { throw "Tidak ada EPS yang dihasilkan." }
      if ($nEps -gt 0 -and $partial6v.Count -gt 0) {
        $miss6v = Get-MissingBasenames $svgDir $epsDir "*.eps" "*.svg"
        if ($miss6v.Count -gt 0) {
          Write-Host ("  [!] Convert EPS sebagian gagal (exit {0}), lanjut dengan file sukses." -f $code) -ForegroundColor Yellow
          Write-FailedList (Join-Path $stock "failed_06_svg-eps.txt") $miss6v
          Add-Stage 6 "SVG->EPS" "PARTIAL" "$nEps file, gagal: $($partial6v -join '+')"
        } else {
          Add-Stage 6 "SVG->EPS" "OK" "$nEps file"
        }
      } else {
        Add-Stage 6 "SVG->EPS" "OK" "$nEps file"
      }
      $vecSrc = $epsDir; $vecKind = "eps"; $vecFilter = "*.eps"
    }

    # ---------- TAHAP 7V: embed paket vektor (folder terpisah, JPG tidak ditimpa) ----------
    Write-Stage 7 "Embed metadata vektor (Adobe + Dreamstime)"
    # Paket vektor di folder terpisah (for_adobe_svg/for_adobe_eps) agar
    # hasil jalur JPG (for_adobe/for_dreamstime) tidak tertimpa.
    # Bersihkan pasangan basi di dalam folder vektor sendiri saja.
    $staleFilter = if ($vecKind -eq "svg") { "*.eps" } else { "*.svg" }
    foreach ($d in @($forAdobe, $forDream)) {
      Get-ChildItem -LiteralPath $d -File -Filter $staleFilter -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
    }
    $vemb = @{ CsvPath = $adobeCsv; JpgDir = $prevDir; VecDir = $vecSrc; OutDir = $forAdobe; VecKind = $vecKind }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-VectorMetadata.ps1") $vemb
    if ($code -ne 0) { Write-Host "  [!] Embed Adobe sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
    $vemb = @{ CsvPath = $dreamCsv; JpgDir = $prevDir; VecDir = $vecSrc; OutDir = $forDream; VecKind = $vecKind }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-VectorMetadata.ps1") $vemb
    if ($code -ne 0) { Write-Host "  [!] Embed Dreamstime sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
    $nA = @(Get-ChildItem -LiteralPath $forAdobe -File -Filter $vecFilter).Count
    $nD = @(Get-ChildItem -LiteralPath $forDream -File -Filter $vecFilter).Count
    Write-Host ("  Siap upload: Adobe={0}, Dreamstime={1} (pasangan JPG+{2})." -f $nA, $nD, $vecKind.ToUpper()) -ForegroundColor Green
    Add-Stage 7 "Embed vektor" "OK" "Adobe=$nA, Dreamstime=$nD"
    }

  } catch {
    Write-Host ("  [FATAL] {0}" -f $_.Exception.Message) -ForegroundColor Red
    Add-Stage "!" "BERHENTI" "FATAL" $_.Exception.Message
  } finally {
    $script:swTotal.Stop()
    Write-Host ""
    Write-Host "  +==========================================+" -ForegroundColor Yellow
    Write-Host "  |  ORCHESTRATOR SUMMARY                   |" -ForegroundColor Yellow
    Write-Host "  +==========================================+" -ForegroundColor Yellow
    foreach ($s in $script:stages) {
      $c = if ($s.Status -eq "OK" -or $s.Status -eq "SKIP") { "Green" }
           elseif ($s.Status -eq "PARTIAL") { "Yellow" }
           else { "Red" }
      Write-Host ("   [{0}] {1,-14} {2,-6} {3}" -f $s.No, $s.Tahap, $s.Status, $s.Detail) -ForegroundColor $c
    }
    $hasPartial = ($script:stages | Where-Object { $_.Status -eq "PARTIAL" }).Count -gt 0
    $hasFatal = ($script:stages | Where-Object { $_.Status -notin @("OK", "SKIP", "PARTIAL") }).Count -gt 0
    if ($hasPartial -and (-not $hasFatal)) {
      Write-Host ""
      Write-Host "  Pemulihan: perbaiki file di failed_*.txt di $stock, lalu rerun perintah yang sama (tanpa -Force)." -ForegroundColor Yellow
      $failedFiles = @(Get-ChildItem -LiteralPath $stock -File -Filter "failed_*.txt" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
      if ($failedFiles.Count -gt 0) {
        Write-Host "  Daftar gagal:" -ForegroundColor Yellow
        foreach ($ff in $failedFiles) {
          Write-Host ("    - {0}" -f (Split-Path $ff -Leaf)) -ForegroundColor Yellow
        }
      }
    }
    Write-Host ("   Total waktu : {0}" -f $script:swTotal.Elapsed.ToString("hh\:mm\:ss"))
    Write-Host ("   Upload Adobe: {0}" -f $forAdobe)
    Write-Host ("   Upload Dream: {0}" -f $forDream)
    Write-Host ("   Log         : {0}" -f (Join-Path $stock "orchestrator.log"))
    Write-Host "  +==========================================+" -ForegroundColor Yellow
    try { Stop-Transcript | Out-Null } catch { }
  }
  $hasFatal = ($script:stages | Where-Object { $_.Status -notin @("OK", "SKIP", "PARTIAL") }).Count -gt 0
  $hasPartial = ($script:stages | Where-Object { $_.Status -eq "PARTIAL" }).Count -gt 0
  $st = if ($hasFatal) { "GAGAL" } elseif ($hasPartial) { "PARTIAL" } else { "OK" }
  return [pscustomobject]@{
    Dir = $SourceDir; Status = $st
    Adobe = $forAdobe; Dream = $forDream
    Waktu = $script:swTotal.Elapsed.ToString("hh\:mm\:ss")
  }
}

function Main {
  $interactive = -not [Console]::IsInputRedirected

  # ---------- Target (menu panah) ----------
  if ([string]::IsNullOrWhiteSpace($Target)) {
    if ($interactive) {
      $Target = Select-Option "Target output" @("JPG", "SVG", "EPS") 0
    } else { $Target = "JPG" }
  }
  $Target = $Target.ToUpper()
  if ($Target -notin @("JPG", "SVG", "EPS")) { Write-Host "  Target tidak dikenal: $Target (pilih JPG/SVG/EPS)." -ForegroundColor Red; exit 1 }

  # ---------- Daftar direktori (boleh >1) ----------
  $dirList = @($SourceDir | ForEach-Object { "$_".Trim().Trim('"').Trim("'") } | Where-Object { $_ })
  if ($dirList.Count -eq 0) {
    if (-not $interactive) { Write-Host "  Mode non-interaktif: isi -SourceDir." -ForegroundColor Red; exit 1 }
    $ans = Read-Host "Direktori berisi image (boleh >1, pisahkan koma)"
    $dirList = @($ans -split "," | ForEach-Object { $_.Trim().Trim('"').Trim("'") } | Where-Object { $_ })
  }
  if ($dirList.Count -eq 0) { Write-Host "  Tidak ada direktori." -ForegroundColor Red; exit 1 }
  $batch = $dirList.Count -gt 1
  $ask = $interactive -and -not $batch

  if ($ask -and $Target -eq "JPG" -and $script:boundKeys -notcontains "Scale") {
    $s = (Read-Host "Skala upscale [2-5, Enter=5]").Trim()
    if ($s -match "^[2-5]$") { $Scale = [int]$s }
  }
  if ($ask -and $script:boundKeys -notcontains "Copyright") {
    $Copyright = Ask-Default "Copyright" $Copyright
    $Creator = Ask-Default "Creator" $Creator
  }
  # Backend metadata dikunci ke API (lokal dinonaktifkan - terlalu lambat).
  $script:MetadataBackend = "api"

  if ($batch) {
    Write-Host ("  Antrean: {0} direktori, config default semua." -f $dirList.Count) -ForegroundColor Yellow
  }

  $grand = [System.Diagnostics.Stopwatch]::StartNew()
  $results = @()
  for ($d = 0; $d -lt $dirList.Count; $d++) {
    if (-not (Test-Path -LiteralPath $dirList[$d] -PathType Container)) {
      Write-Host ("  [X] Folder tidak ada, dilewati: {0}" -f $dirList[$d]) -ForegroundColor Red
      $results += [pscustomobject]@{ Dir = $dirList[$d]; Status = "GAGAL"; Adobe = "-"; Dream = "-"; Waktu = "-" }
      continue
    }
    $results += Process-Dir $dirList[$d] ($d + 1) $dirList.Count
  }
  $grand.Stop()

  if ($batch) {
    Write-Host ""
    Write-Host "  +==========================================+" -ForegroundColor Yellow
    Write-Host "  |  REKAP ANTREAN                          |" -ForegroundColor Yellow
    Write-Host "  +==========================================+" -ForegroundColor Yellow
    foreach ($r in $results) {
      $c = if ($r.Status -eq "OK") { "Green" }
           elseif ($r.Status -eq "PARTIAL") { "Yellow" }
           else { "Red" }
      Write-Host ("   [{0,-5}] {1}" -f $r.Status, $r.Dir) -ForegroundColor $c
    }
    Write-Host ("   Total waktu antrean: {0}" -f $grand.Elapsed.ToString("hh\:mm\:ss"))
    Write-Host "  +==========================================+" -ForegroundColor Yellow
  }
  $failCount = @($results | Where-Object { $_.Status -eq "GAGAL" }).Count
  if ($failCount -gt 0) { exit 1 } else { exit 0 }
}

if ($MyInvocation.InvocationName -ne ".") { Main }

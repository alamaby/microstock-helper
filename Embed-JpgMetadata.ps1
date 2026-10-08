<#
.SYNOPSIS
  Embed Adobe Stock + Dreamstime metadata (Title/Description/Keywords)
  ke file JPG/PNG via ExifTool (triple-sync IPTC+XMP+EXIF).

.DESCRIPTION
  Membaca CSV (Filename/SourceFile,Title,Description,Keywords,Copyright,Creator),
  Keywords dipisah koma. Menulis tiap tag ke 3 grup sekaligus agar
  dibaca kedua agensi:
    Title       -> XMP-dc:Title, IPTC:ObjectName, XMP-photoshop:Headline
    Description -> XMP-dc:Description, IPTC:Caption-Abstract, EXIF:ImageDescription
    Keywords    -> XMP-dc:Subject, IPTC:Keywords (1 entry per keyword)
    Copyright   -> XMP-dc:Rights, IPTC:CopyrightNotice, EXIF:Copyright
    Creator     -> XMP-dc:Creator, IPTC:By-line, EXIF:Artist

  Pencocokan file CERDAS: bila nama di CSV tidak persis sama dengan file
  di folder sumber, skrip mencocokkan via NOMOR 3 DIGIT yang bisa ada di
  mana saja di nama file ("007.jpg" <-> "...__007-Create-....png").
  Angka di dalam tanggal (2026-10-03) dan digit sambung (4+ digit)
  diabaikan otomatis.

  Dijalankan TANPA argumen -> mode interaktif (ditanya folder sumber,
  path CSV, folder output).

.EXAMPLE
  .\Embed-JpgMetadata.ps1
  .\Embed-JpgMetadata.ps1 -CsvPath .\saudi_national_day\jpg-1_metadata_adobe.csv -JpgDir .\saudi_national_day\jpg-1 -OutDir .\saudi_national_day\jpg-1_for_adobe -DryRun
#>
[CmdletBinding()]
param(
  [string]$CsvPath = "",
  [string]$JpgDir = "",
  [string]$OutDir = "",
  [string]$ExifTool = "C:\Apps\exiftool\exiftool.exe",
  [switch]$DryRun,
  [switch]$KeepBackup
)

$ErrorActionPreference = "Stop"

# ---------- Banner ----------
Write-Host @"

  ============================================================
   __  __ ___ ____ ____   ___  ____ _____ ___   ____ _  __
  |  \/  |_ _/ ___|  _ \ / _ \/ ___|_   _/ _ \ / ___| |/ /
  | |\/| || | |   | |_) | | | \___ \ | || | | | |   | ' /
  | |  | || | |___|  _ <| |_| |___) || || |_| | |___| . \
  |_|  |_|___\____|_| \_\\___/|____/ |_| \___/ \____|_|\_\
   EMBED v2.0 - Adobe Stock + Dreamstime triple-sync (ExifTool)
  ============================================================

"@

# ---------- Mode interaktif bila argumen tidak diisi ----------
function Ask-Path($prompt, $mustBe, $default = "") {
  while ($true) {
    $hint = if ($default) { " [Enter=$default]" } else { "" }
    $v = (Read-Host "$prompt$hint").Trim().Trim('"')
    if (-not $v -and $default) { return $default }
    if (-not $v) { continue }
    if ($mustBe -eq "any") { return $v }
    if ($mustBe -eq "dir" -and (Test-Path $v -PathType Container)) { return $v }
    if ($mustBe -eq "file" -and (Test-Path $v -PathType Leaf)) { return $v }
    Write-Host "  (!) tidak ditemukan: $v" -ForegroundColor Yellow
  }
}

$fullyInteractive = ((-not $PSBoundParameters.ContainsKey("JpgDir")) -or -not $JpgDir) -and
                    ((-not $PSBoundParameters.ContainsKey("CsvPath")) -or -not $CsvPath)
if ((-not $PSBoundParameters.ContainsKey("JpgDir")) -or -not $JpgDir) {
  $JpgDir = Ask-Path "Folder sumber berisi file gambar" "dir"
}
if ((-not $PSBoundParameters.ContainsKey("CsvPath")) -or -not $CsvPath) {
  $CsvPath = Ask-Path "Path file CSV metadata" "file"
}
if (-not (Test-Path $JpgDir -PathType Container)) { throw "Folder sumber tidak ada: $JpgDir" }
if (-not (Test-Path $CsvPath -PathType Leaf)) { throw "File CSV tidak ada: $CsvPath" }
if (-not (Test-Path $ExifTool -PathType Leaf)) { throw "ExifTool tidak ada: $ExifTool" }

if (-not $PSBoundParameters.ContainsKey("OutDir") -or -not $OutDir) {
  $suf = if ($CsvPath -match "adobe") { "_for_adobe" }
         elseif ($CsvPath -match "dreamstime") { "_for_dreamstime" }
         else { "_for_upload" }
  $defOut = $JpgDir.TrimEnd("\", "/") + $suf
  if ($fullyInteractive) {
    # Tanpa argumen: tawarkan folder output turunan (sumber tak diubah)
    $OutDir = Ask-Path "Folder output" "any" $defOut
    if ((-not $PSBoundParameters.ContainsKey("DryRun")) -and
        ((Read-Host "DryRun dulu tanpa menulis? [Y/n]").Trim().ToLower() -ne "n")) {
      $DryRun = $true
    }
  } elseif ($PSBoundParameters.ContainsKey("OutDir")) {
    $OutDir = $defOut  # -OutDir "" eksplisit = pakai default turunan
  }
  # else: OutDir tidak diisi + ada argumen lain = embed di tempat (perilaku lama)
}

# ---------- Animasi progress ASCII ----------
$script:spinIdx = 0
function Show-Bar($done, $total, $label) {
  $w = 24
  $p = if ($total -gt 0) { $done / $total } else { 1 }
  $f = [math]::Min($w, [int][math]::Floor($p * $w))
  $bar = if ($f -ge $w) { "=" * $w } else { ("=" * $f) + ">" + ("-" * ($w - $f - 1)) }
  $ch = @("|", "/", "-", "\")[$script:spinIdx % 4]; $script:spinIdx++
  if ($label.Length -gt 42) { $label = "..." + $label.Substring($label.Length - 39) }
  Write-Host ("`r[{0}] {1}/{2} {3} {4}   " -f $bar, $done, $total, $ch, $label) -NoNewline
}

# ---------- Smart-match nomor 3 digit ----------
function Get-FileNumber([string]$name) {
  # Abaikan digit sambung 4+: "2026-10-03" tidak menghasilkan match.
  $best = $null; $bestScore = 0
  foreach ($m in [regex]::Matches($name, "(?<!\d)(\d{3})(?!\d)")) {
    $prev = if ($m.Index -ge 2 -and $name.Substring($m.Index - 2, 2) -eq "__") { "__" }
            elseif ($m.Index -ge 1) { $name[$m.Index - 1] } else { "" }
    $score = if ($prev -eq "__") { 3 } elseif ($prev -eq "_" -or $prev -eq "-" -or $prev -eq "") { 2 } else { 1 }
    if ($score -gt $bestScore) { $bestScore = $score; $best = $m.Groups[1].Value }
    elseif ($score -eq $bestScore -and $best -ne $m.Groups[1].Value) { $best = $null }  # ambigu
  }
  return $best
}

function Get-CsvSourceFile($row) {
  # Template resmi Adobe memakai header Filename; CSV lama memakai SourceFile.
  if ($row.Filename) { return $row.Filename }
  return $row.SourceFile
}

function Test-RealFormat($path) {
  # Pastikan isi file sesuai ekstensi (exiftool menolak isi PNG bernama .jpg)
  $ext = [IO.Path]::GetExtension($path).ToLower()
  $fs = [IO.File]::OpenRead($path); $mg = New-Object byte[] 4
  [void]$fs.Read($mg, 0, 4); $fs.Close()
  $isJpg = ($mg[0] -eq 0xFF -and $mg[1] -eq 0xD8)
  $isPng = ($mg[0] -eq 0x89 -and $mg[1] -eq 0x50)
  if ($ext -eq ".jpg" -and -not $isJpg) { return "isi BUKAN jpeg (magic: $(($mg | ForEach-Object { $_.ToString('X2') }) -join ' '))" }
  if ($ext -eq ".png" -and -not $isPng) { return "isi BUKAN png" }
  return ""
}

# ---------- Proses utama ----------
$rows = @(Import-Csv $CsvPath -Encoding UTF8)
$dirFiles = @(Get-ChildItem $JpgDir -File | Select-Object -ExpandProperty Name)
if ($OutDir) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }
$ok = 0; $fail = 0; $i = 0

Write-Host "CSV : $CsvPath ($($rows.Count) baris)"
Write-Host "Dari: $JpgDir"
Write-Host ($(if ($OutDir) { "Ke  : $OutDir" } else { "Ke  : (langsung di folder sumber)" }))
if ($DryRun) { Write-Host "*** DRYRUN - tidak ada file yang ditulis ***" -ForegroundColor Cyan }
Write-Host ""

foreach ($r in $rows) {
  $i++
  $srcName = Get-CsvSourceFile $r
  # 1) nama persis, 2) nomor 3 digit
  $hit = @($dirFiles | Where-Object { $_ -ieq $srcName })
  $via = "exact"
  if (-not $hit) {
    $num = Get-FileNumber $srcName
    if ($num) { $hit = @($dirFiles | Where-Object { (Get-FileNumber $_) -eq $num }) }
    if ($hit.Count -eq 1) { $via = "#$num" } else { $hit = @() }
  }
  if (-not $hit) { Write-Warning "SKIP (tak cocok): $srcName"; $fail++; Show-Bar $i $rows.Count $srcName; continue }
  $actual = $hit[0]
  $src = Join-Path $JpgDir $actual

  $fmtErr = Test-RealFormat $src
  if ($fmtErr) { Write-Warning "SKIP ($fmtErr): $actual - konversi dulu ke format asli"; $fail++; Show-Bar $i $rows.Count $actual; continue }

  $file = $src
  if ($OutDir) {
    $file = Join-Path $OutDir $actual
    if (-not $DryRun) { Copy-Item $src $file -Force }
  }

  $kws = @($r.Keywords -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }) |
    Select-Object -Unique
  $isDream = $CsvPath -match "dreamstime"
  if (-not $isDream -and $r.Title.Length -gt 70) { Write-Warning "$actual : Title $($r.Title.Length)ch > 70 (Adobe ideal)" }
  if ($r.Title.Length -gt 200) { Write-Warning "$actual : Title $($r.Title.Length)ch > 200 (Dreamstime maks)" }
  if (-not $isDream -and $kws.Count -gt 49) { Write-Warning "$actual : $($kws.Count) keywords > 49 (Adobe maks)" }
  if ($isDream -and $kws.Count -gt 80) { Write-Warning "$actual : $($kws.Count) keywords > 80 (Dreamstime maks kata tunggal)" }
  if (-not $r.Description) { Write-Warning "$actual : Description kosong" }

  Show-Bar $i $rows.Count $actual
  if ($DryRun) { continue }

  # Fase 1: reset (invocasi terpisah; clear+add se-invocasi menduplikasi list)
  $reset = @("-XMP-dc:Title=", "-IPTC:ObjectName=", "-XMP-photoshop:Headline=",
    "-XMP-dc:Description=", "-IPTC:Caption-Abstract=", "-EXIF:ImageDescription=",
    "-IPTC:Keywords=", "-XMP-dc:Subject=")
  if ($r.Copyright) { $reset += "-XMP-dc:Rights=", "-IPTC:CopyrightNotice=", "-EXIF:Copyright=" }
  if ($r.Creator) { $reset += "-XMP-dc:Creator=", "-IPTC:By-line=", "-EXIF:Artist=" }
  if (-not $KeepBackup) { $reset = @("-overwrite_original") + $reset }
  & $ExifTool ($reset + @("-P", "-m", $file)) | Out-Null

  # Fase 2: tulis bersih (PNG via XMP saja; IPTC dipetakan ke XMP oleh exiftool)
  $isPng = [IO.Path]::GetExtension($file) -ieq ".png"
  $args = @()
  if (-not $KeepBackup) { $args += "-overwrite_original" }
  $args += "-P", "-m", "-IPTC:CodedCharacterSet=UTF8"
  $args += "-XMP-dc:Title=$($r.Title)", "-IPTC:ObjectName=$($r.Title)", "-XMP-photoshop:Headline=$($r.Title)"
  $args += "-XMP-dc:Description=$($r.Description)", "-IPTC:Caption-Abstract=$($r.Description)", "-EXIF:ImageDescription=$($r.Description)"
  foreach ($k in $kws) { if (-not $isPng) { $args += "-IPTC:Keywords+=$k" }; $args += "-XMP-dc:Subject+=$k" }
  if ($r.Copyright) { $args += "-XMP-dc:Rights=$($r.Copyright)", "-IPTC:CopyrightNotice=$($r.Copyright)", "-EXIF:Copyright=$($r.Copyright)" }
  if ($r.Creator) { $args += "-XMP-dc:Creator=$($r.Creator)", "-IPTC:By-line=$($r.Creator)", "-EXIF:Artist=$($r.Creator)" }
  $args += $file
  & $ExifTool @args | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Warning "GAGAL: $actual"; $fail++; continue }

  $kwTag = if ($isPng) { "XMP-dc:Subject" } else { "IPTC:Keywords" }
  $kwBack = @((& $ExifTool -s -s -s -$kwTag $file) -split ',\s*' | Where-Object { $_ })
  $kwUniq = @($kwBack | Select-Object -Unique)
  $titleOk = (& $ExifTool -s -s -s -XMP-dc:Title $file) -eq $r.Title
  $tag = if ($via -eq "exact") { "OK" } else { "OK[auto$via]" }
  if ($kwBack.Count -eq $kws.Count -and $kwUniq.Count -eq $kws.Count -and $titleOk) {
    Write-Output "$tag $actual [KW=$($kwBack.Count)]"
    $ok++
  } else {
    Write-Warning "PERIKSA $actual [KW total=$($kwBack.Count) unik=$($kwUniq.Count) ekspektasi=$($kws.Count), Title OK: $titleOk]"
    $fail++
  }
}

Write-Host ""
Write-Host ""
if ($fail -eq 0) {
  Write-Host "  ____   ___  _   _ _____" -ForegroundColor Green
  Write-Host " |  _ \ / _ \| \ | | ____|" -ForegroundColor Green
  Write-Host " | | | | | | |  \| |  _|" -ForegroundColor Green
  Write-Host " | |_| | |_| | |\  | |___" -ForegroundColor Green
  Write-Host " |____/ \___/|_| \_|_____|" -ForegroundColor Green
  Write-Host ("  Selesai: {0} OK, {1} gagal dari {2} baris." -f $ok, $fail, $rows.Count) -ForegroundColor Green
} else {
  Write-Host ("  Selesai: {0} OK, {1} gagal/skip dari {2} baris." -f $ok, $fail, $rows.Count) -ForegroundColor Yellow
}
if ($DryRun) { Write-Host "  (DryRun - ulangi tanpa -DryRun untuk tulis asli)" -ForegroundColor Cyan }

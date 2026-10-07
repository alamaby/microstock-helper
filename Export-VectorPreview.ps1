<#
.SYNOPSIS
  Render SVG menjadi JPG preview besar via Inkscape + ffmpeg.

.DESCRIPTION
  Untuk paket upload vektor dibutuhkan JPG preview beresolusi besar
  dengan basename SAMA dengan file vektor. Preview di-render dari SVG
  (render vektor asli, tanpa artefak AI-upscale):
    Inkscape svg --export-type=png --export-width=Width -> PNG
    ffmpeg PNG -q:v 1 -> JPG (nama dipertahankan)

  Default Width=6000 (sisi lebar; sisi lain mengikuti aspek) - di atas
  syarat minimum preview agensi dengan margin. Idempoten: JPG yang sudah
  ada dan valid di-skip (kecuali -Force). Tulis atomis via .tmp.

.EXAMPLE
  .\Export-VectorPreview.ps1 -SvgDir .\s -OutDir .\p
  .\Export-VectorPreview.ps1 -SvgDir .\a -OutDir .\b -Width 5000 -Force
#>
[CmdletBinding()]
param(
  [string]$SvgDir = "",
  [string]$OutDir = "",
  [ValidateRange(1000, 15000)][int]$Width = 6000,
  [ValidateRange(1, 31)][int]$Quality = 1,
  [string]$Inkscape = "C:\Program Files\Inkscape\bin\inkscape.com",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$TmpDir = "C:\Users\alama\AppData\Local\Temp\opencode"

Write-Host ""
Write-Host "  PREVIEW - SVG to large JPG (Inkscape + ffmpeg)" -ForegroundColor Cyan
Write-Host ""

function Read-Folder($Prompt) {
  while ($true) {
    $v = (Read-Host $Prompt).Trim().Trim('"').Trim("'")
    if ($v -ne "" -and (Test-Path -LiteralPath $v -PathType Container)) { return (Get-Item -LiteralPath $v).FullName }
    Write-Host "  Folder tidak ditemukan, coba lagi." -ForegroundColor Red
  }
}

$script:ffprobeOk = [bool](Get-Command ffprobe -ErrorAction SilentlyContinue)
function Test-JpgOk([string]$path) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
  try {
    $fs = [IO.File]::OpenRead($path); $len = $fs.Length
    if ($len -lt 100) { $fs.Close(); return $false }
    $h = New-Object byte[] 2; [void]$fs.Read($h, 0, 2)
    $isJpg = ($h[0] -eq 0xFF -and $h[1] -eq 0xD8)
    $fs.Seek(-2, [IO.SeekOrigin]::End) | Out-Null
    $t = New-Object byte[] 2; [void]$fs.Read($t, 0, 2)
    $fs.Close()
    if (-not ($isJpg -and $t[0] -eq 0xFF -and $t[1] -eq 0xD9)) { return $false }
  } catch { return $false }
  if ($script:ffprobeOk) {
    & ffprobe -v error -select_streams v:0 -show_entries stream=codec_name `
      -of default=nw=1:nk=1 -- "$path" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
  }
  return $true
}

function Show-Bar($Done, $Total, $Width2 = 30) {
  if ($Total -eq 0) { $Total = 1 }
  $pct = [int]($Done * 100 / $Total)
  $fill = [int]($Done * $Width2 / $Total)
  return ("[" + ("#" * $fill) + ("-" * ($Width2 - $fill)) + "] $pct%")
}

if (-not (Test-Path -LiteralPath $Inkscape -PathType Leaf)) {
  Write-Host "  [X] inkscape.com tidak ditemukan: $Inkscape" -ForegroundColor Red
  exit 1
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "  [X] ffmpeg tidak ditemukan di PATH." -ForegroundColor Red
  exit 1
}
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

if ([string]::IsNullOrWhiteSpace($SvgDir) -or -not (Test-Path -LiteralPath $SvgDir -PathType Container)) {
  $SvgDir = Read-Folder "Folder INPUT (berisi SVG)"
} else {
  $SvgDir = (Get-Item -LiteralPath $SvgDir.Trim().Trim('"')).FullName
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = (Read-Host "Folder OUTPUT (preview JPG, dibuat otomatis bila belum ada)").Trim().Trim('"').Trim("'")
  if ([string]::IsNullOrWhiteSpace($OutDir)) { Write-Host "  Folder output wajib diisi." -ForegroundColor Red; exit 1 }
}
$OutDir = $OutDir.Trim().Trim('"').Trim("'")
if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
  New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
  Write-Host "  Folder output dibuat: $OutDir" -ForegroundColor Green
}
$OutDir = (Get-Item -LiteralPath $OutDir).FullName
if ($SvgDir -eq $OutDir) { Write-Host "Folder input dan output tidak boleh sama." -ForegroundColor Red; exit 1 }

$files = Get-ChildItem -LiteralPath $SvgDir -File |
  Where-Object { $_.Extension -ieq ".svg" } |
  Sort-Object Name

Write-Host ""
Write-Host "  Inkscape: $Inkscape" -ForegroundColor Gray
Write-Host "  Lebar   : $Width px, ffmpeg q:v=$Quality" -ForegroundColor Gray
Write-Host "  Input   : $SvgDir" -ForegroundColor Gray
Write-Host "  Output  : $OutDir" -ForegroundColor Gray
Write-Host "  File    : $($files.Count) SVG ditemukan" -ForegroundColor Gray
if ($files.Count -eq 0) { Write-Host "  Tidak ada SVG untuk diproses." -ForegroundColor Yellow; exit 0 }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$done = 0; $ok = 0; $skipped = 0; $failed = 0
$failedFiles = @()

for ($idx = 0; $idx -lt $files.Count; $idx++) {
  $f = $files[$idx]
  $dest = Join-Path $OutDir ($f.BaseName + ".jpg")
  $num = "[{0}/{1}]" -f ($idx + 1), $files.Count

  if ((Test-JpgOk $dest) -and (-not $Force)) {
    Write-Host "$num SKIP  $($f.BaseName).jpg (sudah ada)  $(Show-Bar $done $files.Count)" -ForegroundColor DarkGray
    $skipped++; $done++
    continue
  }

  Write-Host "$num RENDER $($f.Name)" -ForegroundColor White
  $tmpSvg = Join-Path $TmpDir "p_in.svg"
  $tmpPng = Join-Path $TmpDir "p_mid.png"
  $tmpJpg = Join-Path $TmpDir "p_out.jpg"
  Remove-Item $tmpSvg, $tmpPng, $tmpJpg -Force -ErrorAction SilentlyContinue
  try {
    Copy-Item -LiteralPath $f.FullName -Destination $tmpSvg -Force
    & $Inkscape $tmpSvg --export-type=png --export-width=$Width --export-filename=$tmpPng 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tmpPng)) { throw "inkscape export PNG gagal (exit $LASTEXITCODE)." }
    & ffmpeg -y -loglevel warning -i "$tmpPng" -q:v $Quality "$tmpJpg" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "ffmpeg PNG->JPG gagal (exit $LASTEXITCODE)." }
    if (-not (Test-JpgOk $tmpJpg)) { throw "hasil JPG tidak valid." }
    $tmpDest = "$dest.tmp.jpg"
    Copy-Item $tmpJpg -Destination $tmpDest -Force
    Move-Item -LiteralPath $tmpDest -Destination $dest -Force
    $mb = [math]::Round(((Get-Item -LiteralPath $dest).Length / 1MB), 2)
    Write-Host "   OK (${mb}MB)" -ForegroundColor Green
    $ok++
  } catch {
    Write-Host "   GAGAL: $($_.Exception.Message)" -ForegroundColor Red
    $failed++; $failedFiles += $f.FullName
  } finally {
    Remove-Item $tmpSvg, $tmpPng, $tmpJpg -Force -ErrorAction SilentlyContinue
  }
  $done++
  Write-Host "   $(Show-Bar $done $files.Count)" -ForegroundColor DarkGray
}
$sw.Stop()

Write-Host ""
Write-Host "  +==========================================+" -ForegroundColor Yellow
Write-Host "  |  PREVIEW SUMMARY                        |" -ForegroundColor Yellow
Write-Host "  +==========================================+" -ForegroundColor Yellow
Write-Host ("   Total file    : {0}" -f $files.Count)
Write-Host ("   Berhasil      : {0}" -f $ok) -ForegroundColor Green
Write-Host ("   Skip (ada)    : {0}" -f $skipped) -ForegroundColor DarkGray
if ($failed -gt 0) { Write-Host ("   Gagal         : {0}" -f $failed) -ForegroundColor Red }
else { Write-Host ("   Gagal         : {0}" -f $failed) }
Write-Host ("   Total waktu   : {0}" -f $sw.Elapsed.ToString('hh\:mm\:ss'))
Write-Host ("   Output        : {0}" -f $OutDir)
Write-Host "  +==========================================+" -ForegroundColor Yellow
if ($failedFiles.Count -gt 0) {
  Write-Host "  File gagal:" -ForegroundColor Red
  $failedFiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
  exit 1
}

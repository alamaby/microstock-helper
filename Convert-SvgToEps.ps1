<#
.SYNOPSIS
  Batch konversi SVG ke EPS via Inkscape CLI.

.DESCRIPTION
  Mengonversi semua *.svg di SvgDir menjadi *.eps (basename sama) via:
    inkscape in.svg --export-type=eps --export-filename=out.eps
  (Inkscape 1.4.3 di C:\Program Files\Inkscape\bin\inkscape.com).

  Dipakai untuk jalur EPS setelah SVG tersedia dari Trace-Svg.ps1.
  Sesuai keputusan: paket EPS berisi .eps + .jpg saja (SVG intermediate
  tidak ikut dikirim). Idempoten: EPS yang sudah ada dan valid di-skip
  (kecuali -Force). Tulis atomis via .tmp.

.EXAMPLE
  .\Convert-SvgToEps.ps1 -SvgDir .\batch\_stock\05_svg -OutDir .\batch\_stock\07_eps
  .\Convert-SvgToEps.ps1 -SvgDir .\a -OutDir .\b -Force
#>
[CmdletBinding()]
param(
  [string]$SvgDir = "",
  [string]$OutDir = "",
  [string]$Inkscape = "C:\Program Files\Inkscape\bin\inkscape.com",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$TmpDir = "C:\Users\alama\AppData\Local\Temp\opencode"

Write-Host ""
Write-Host "  EPS - SVG to EPS batch (Inkscape CLI)" -ForegroundColor Cyan
Write-Host ""

function Read-Folder($Prompt) {
  while ($true) {
    $v = (Read-Host $Prompt).Trim().Trim('"').Trim("'")
    if ($v -ne "" -and (Test-Path -LiteralPath $v -PathType Container)) { return (Get-Item -LiteralPath $v).FullName }
    Write-Host "  Folder tidak ditemukan, coba lagi." -ForegroundColor Red
  }
}

function Test-EpsOk([string]$path) {
  # Valid bila ada, tak kosong, diawali header PostScript %!PS.
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
  try {
    if ((Get-Item -LiteralPath $path).Length -lt 100) { return $false }
    $fs = [IO.File]::OpenRead($path); $mg = New-Object byte[] 4
    [void]$fs.Read($mg, 0, 4); $fs.Close()
    return ($mg[0] -eq 0x25 -and $mg[1] -eq 0x21 -and $mg[2] -eq 0x50 -and $mg[3] -eq 0x53)
  } catch { return $false }
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
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

if ([string]::IsNullOrWhiteSpace($SvgDir) -or -not (Test-Path -LiteralPath $SvgDir -PathType Container)) {
  $SvgDir = Read-Folder "Folder INPUT (berisi SVG)"
} else {
  $SvgDir = (Get-Item -LiteralPath $SvgDir.Trim().Trim('"')).FullName
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = (Read-Host "Folder OUTPUT (hasil EPS, dibuat otomatis bila belum ada)").Trim().Trim('"').Trim("'")
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
Write-Host "  Input   : $SvgDir" -ForegroundColor Gray
Write-Host "  Output  : $OutDir" -ForegroundColor Gray
Write-Host "  File    : $($files.Count) SVG ditemukan" -ForegroundColor Gray
if ($files.Count -eq 0) { Write-Host "  Tidak ada SVG untuk diproses." -ForegroundColor Yellow; exit 0 }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$done = 0; $ok = 0; $skipped = 0; $failed = 0
$failedFiles = @()

for ($idx = 0; $idx -lt $files.Count; $idx++) {
  $f = $files[$idx]
  $dest = Join-Path $OutDir ($f.BaseName + ".eps")
  $num = "[{0}/{1}]" -f ($idx + 1), $files.Count

  if ((Test-EpsOk $dest) -and (-not $Force)) {
    Write-Host "$num SKIP  $($f.BaseName).eps (sudah ada)  $(Show-Bar $done $files.Count)" -ForegroundColor DarkGray
    $skipped++; $done++
    continue
  }

  Write-Host "$num CONVERT $($f.Name)" -ForegroundColor White
  $tmpSvg = Join-Path $TmpDir "e_in.svg"
  $tmpEps = Join-Path $TmpDir "e_out.eps"
  Remove-Item $tmpSvg, $tmpEps -Force -ErrorAction SilentlyContinue
  try {
    Copy-Item -LiteralPath $f.FullName -Destination $tmpSvg -Force
    & $Inkscape $tmpSvg --export-type=eps --export-filename=$tmpEps 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-EpsOk $tmpEps)) { throw "inkscape export EPS gagal (exit $LASTEXITCODE)." }
    $tmpDest = "$dest.tmp"
    Copy-Item $tmpEps -Destination $tmpDest -Force
    Move-Item -LiteralPath $tmpDest -Destination $dest -Force
    $kb = [math]::Round(((Get-Item -LiteralPath $dest).Length / 1KB), 1)
    Write-Host "   OK (${kb}KB)" -ForegroundColor Green
    $ok++
  } catch {
    Write-Host "   GAGAL: $($_.Exception.Message)" -ForegroundColor Red
    $failed++; $failedFiles += $f.FullName
  } finally {
    Remove-Item $tmpSvg, $tmpEps -Force -ErrorAction SilentlyContinue
  }
  $done++
  Write-Host "   $(Show-Bar $done $files.Count)" -ForegroundColor DarkGray
}
$sw.Stop()

Write-Host ""
Write-Host "  +==========================================+" -ForegroundColor Yellow
Write-Host "  |  SVG-EPS SUMMARY                        |" -ForegroundColor Yellow
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

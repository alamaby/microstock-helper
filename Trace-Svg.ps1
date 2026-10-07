<#
.SYNOPSIS
  Trace semua JPG kecil dalam satu folder menjadi SVG via vtracer CLI.

.DESCRIPTION
  Memproses semua *.jpg / *.jpeg di InputDir menjadi *.svg (basename sama)
  memakai default yang sudah terverifikasi di mesin ini:
    vtracer --clustering color-cluster --hierarchical cutout --mode spline
  (vtracer 1.0.0-alpha.4 di C:\Apps\vtracer.exe).

  Trace dilakukan dari JPG KECIL (bukan hasil upscale): vektor di-scale
  tak terbatas, file kecil = trace cepat + SVG ramping. Preview besar
  untuk upload dibuat terpisah dari SVG via Export-VectorPreview.ps1.

  Idempoten: SVG yang sudah ada dan valid di-skip (kecuali -Force).
  Output ditulis atomis (via .tmp) agar interupsi tak meninggalkan
  file setengah-jadi. Workaround MAX_PATH: file disalin ke nama pendek
  di TEMP, diproses di sana, hasilnya disalin kembali dengan nama asli
  (pola yang sama dengan Upscale.ps1).

.EXAMPLE
  .\Trace-Svg.ps1 -InputDir .\batch\_stock\02_jpg_small -OutDir .\batch\_stock\05_svg
  .\Trace-Svg.ps1 -InputDir .\a -OutDir .\b -Force
#>
[CmdletBinding()]
param(
  [string]$InputDir = "",
  [string]$OutDir = "",
  [string]$Vtracer = "C:\Apps\vtracer.exe",
  [ValidateSet("color-cluster", "bw", "watershed")][string]$Clustering = "color-cluster",
  [ValidateSet("stacked", "cutout")][string]$Hierarchical = "cutout",
  [ValidateSet("pixel", "polygon", "spline")][string]$Mode = "spline",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$TmpDir = "C:\Users\alama\AppData\Local\Temp\opencode"

Write-Host ""
Write-Host "  __   _______ ____      _    ____ _____ ____  " -ForegroundColor Cyan
Write-Host "  \ \ / /_  _|  _ \    / \  / ___| ____|  _ \ " -ForegroundColor Cyan
Write-Host "   \ V /  | | | |_) |  / _ \| |   |  _| | |_) |" -ForegroundColor Cyan
Write-Host "    | |   | | |  _ <  / ___ \ |___| |___|  _ < " -ForegroundColor Cyan
Write-Host "    |_|   |_| |_| \_\/_/   \_\____|_____|_| \_\" -ForegroundColor Cyan
Write-Host "   JPG -> SVG batch tracer (vtracer, color/cutout/spline)" -ForegroundColor Gray
Write-Host ""

function Read-Folder($Prompt) {
  while ($true) {
    $v = (Read-Host $Prompt).Trim().Trim('"').Trim("'")
    if ($v -ne "" -and (Test-Path -LiteralPath $v -PathType Container)) { return (Get-Item -LiteralPath $v).FullName }
    Write-Host "  Folder tidak ditemukan, coba lagi." -ForegroundColor Red
  }
}

function Test-SvgOk([string]$path) {
  # Valid bila ada, tak kosong, dan berisi tag <svg (bukan file setengah-jadi).
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
  try {
    $len = (Get-Item -LiteralPath $path).Length
    if ($len -lt 50) { return $false }
    $head = (Get-Content -LiteralPath $path -TotalCount 5 -ErrorAction Stop) -join "`n"
    return ($head -match "<svg")
  } catch { return $false }
}

function Show-Bar($Done, $Total, $Width = 30) {
  if ($Total -eq 0) { $Total = 1 }
  $pct = [int]($Done * 100 / $Total)
  $fill = [int]($Done * $Width / $Total)
  return ("[" + ("#" * $fill) + ("-" * ($Width - $fill)) + "] $pct%")
}

if (-not (Test-Path -LiteralPath $Vtracer -PathType Leaf)) {
  Write-Host "  [X] vtracer.exe tidak ditemukan: $Vtracer" -ForegroundColor Red
  exit 1
}
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

if ([string]::IsNullOrWhiteSpace($InputDir) -or -not (Test-Path -LiteralPath $InputDir -PathType Container)) {
  $InputDir = Read-Folder "Folder INPUT (berisi JPG kecil)"
} else {
  $InputDir = (Get-Item -LiteralPath $InputDir.Trim().Trim('"')).FullName
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = (Read-Host "Folder OUTPUT (hasil SVG, dibuat otomatis bila belum ada)").Trim().Trim('"').Trim("'")
  if ([string]::IsNullOrWhiteSpace($OutDir)) { Write-Host "  Folder output wajib diisi." -ForegroundColor Red; exit 1 }
}
$OutDir = $OutDir.Trim().Trim('"').Trim("'")
if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
  New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
  Write-Host "  Folder output dibuat: $OutDir" -ForegroundColor Green
}
$OutDir = (Get-Item -LiteralPath $OutDir).FullName
if ($InputDir -eq $OutDir) { Write-Host "Folder input dan output tidak boleh sama." -ForegroundColor Red; exit 1 }

$files = Get-ChildItem -LiteralPath $InputDir -File |
  Where-Object { $_.Extension -match '^\.jpe?g$' } |
  Sort-Object Name

Write-Host ""
Write-Host "  vtracer : $Vtracer" -ForegroundColor Gray
Write-Host "  Flags   : --clustering $Clustering --hierarchical $Hierarchical --mode $Mode" -ForegroundColor Gray
Write-Host "  Input   : $InputDir" -ForegroundColor Gray
Write-Host "  Output  : $OutDir" -ForegroundColor Gray
Write-Host "  File    : $($files.Count) JPG ditemukan" -ForegroundColor Gray
if ($files.Count -eq 0) { Write-Host "  Tidak ada JPG untuk diproses." -ForegroundColor Yellow; exit 0 }

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$done = 0; $ok = 0; $skipped = 0; $failed = 0
$failedFiles = @()
$frames = @('|', '/', '-', '\')

for ($idx = 0; $idx -lt $files.Count; $idx++) {
  $f = $files[$idx]
  $dest = Join-Path $OutDir ($f.BaseName + ".svg")
  $num = "[{0}/{1}]" -f ($idx + 1), $files.Count

  if ((Test-SvgOk $dest) -and (-not $Force)) {
    Write-Host "$num SKIP  $($f.BaseName).svg (sudah ada)  $(Show-Bar $done $files.Count)" -ForegroundColor DarkGray
    $skipped++; $done++
    continue
  }

  Write-Host "$num TRACE $($f.Name)" -ForegroundColor White
  $t0 = [System.Diagnostics.Stopwatch]::StartNew()
  # Nama pendek di TEMP (hindari MAX_PATH 260); ekstensi asli dipertahankan.
  $tmpIn = Join-Path $TmpDir ("t_in" + $f.Extension.ToLower())
  $tmpOut = Join-Path $TmpDir "t_out.svg"
  Remove-Item $tmpIn, $tmpOut -Force -ErrorAction SilentlyContinue
  try {
    Copy-Item -LiteralPath $f.FullName -Destination $tmpIn -Force
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Vtracer
    $psi.Arguments = "--input `"$tmpIn`" --output `"$tmpOut`" --clustering $Clustering --hierarchical $Hierarchical --mode $Mode"
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardOutput = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    $fi = 0
    while (-not $p.HasExited) {
      $ch = $frames[$fi % $frames.Count]; $fi++
      Write-Host "`r   $ch tracing... $($t0.Elapsed.ToString('mm\:ss')) " -NoNewline -ForegroundColor Cyan
      Start-Sleep -Milliseconds 150
    }
    $p.WaitForExit()
    $good = ($p.ExitCode -eq 0) -and (Test-SvgOk $tmpOut)
    if ($good) {
      $tmpDest = "$dest.tmp"
      Copy-Item $tmpOut -Destination $tmpDest -Force
      Move-Item -LiteralPath $tmpDest -Destination $dest -Force
      $dur = $t0.Elapsed.ToString('mm\:ss')
      $kb = [math]::Round(((Get-Item -LiteralPath $dest).Length / 1KB), 1)
      Write-Host "`r   OK ${dur} (${kb}KB)      " -ForegroundColor Green
      $ok++
    } else {
      Write-Host "`r   GAGAL (exit=$($p.ExitCode))" -ForegroundColor Red
      $failed++; $failedFiles += $f.FullName
    }
  } catch {
    Write-Host "`r   GAGAL: $($_.Exception.Message)" -ForegroundColor Red
    $failed++; $failedFiles += $f.FullName
  } finally {
    Remove-Item $tmpIn, $tmpOut -Force -ErrorAction SilentlyContinue
  }
  $done++
  Write-Host "   $(Show-Bar $done $files.Count)" -ForegroundColor DarkGray
}
$sw.Stop()

Write-Host ""
Write-Host "  +==========================================+" -ForegroundColor Yellow
Write-Host "  |  TRACE SUMMARY                          |" -ForegroundColor Yellow
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
  Write-Host '  File gagal:' -ForegroundColor Red
  $failedFiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
  if (($ok + $skipped) -eq 0) { exit 1 }
}
exit 0

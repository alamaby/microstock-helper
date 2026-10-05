<#
.SYNOPSIS
  Batch convert PNG ke JPG via ffmpeg, dengan animasi ASCII + ringkasan progres.

.DESCRIPTION
  Meminta direktori sumber dan direktori output (via parameter atau prompt
  interaktif), lalu mengonversi semua file *.png menjadi *.jpg (nama
  dipertahankan) memakai:  ffmpeg -q:v <Quality>  (default 1 = kualitas terbaik).

  Fitur:
    - Animasi spinner ASCII per file + progres keseluruhan [i/N].
    - Idempoten: file output yang sudah ada di-skip (kecuali -Force).
    - Aman untuk nama file bervolume spesial (spasi, koma, path panjang):
      memakai LiteralPath + argumen ffmpeg yang dikutip.
    - Ringkasan akhir: total / converted / skipped / failed + durasi.

.EXAMPLE
  .\Convert-PngToJpg.ps1
  (ditanya SourceDir dan OutDir secara interaktif)

.EXAMPLE
  .\Convert-PngToJpg.ps1 -SourceDir .\upscaled-1 -OutDir .\jpg-1

.EXAMPLE
  .\Convert-PngToJpg.ps1 -SourceDir .\a -OutDir .\b -Quality 2 -Force -Recurse
#>
[CmdletBinding()]
param(
  [string]$SourceDir = '',
  [string]$OutDir = '',
  [ValidateRange(1, 31)][int]$Quality = 1,
  [switch]$Force,
  [switch]$Recurse
)

$ErrorActionPreference = 'Stop'

# ---------- Banner ----------
Write-Host ''
Write-Host '  ____  _   _  ____       _ ____   ____   ____ ' -ForegroundColor Cyan
Write-Host ' |  _ \| \ | |/ ___|     | |  _ \ / ___| / ___|' -ForegroundColor Cyan
Write-Host ' | |_) |  \| | |  _ _____| | |_) | |  _ | |    ' -ForegroundColor Cyan
Write-Host ' |  __/| |\  | |_| |_____| |  __/| |_| || |___ ' -ForegroundColor Cyan
Write-Host ' |_|   |_| \_|\____|     |_|_|    \____(_)____|' -ForegroundColor Cyan
Write-Host '   PNG -> JPG batch converter (ffmpeg)' -ForegroundColor Gray
Write-Host ''

# ---------- ffmpeg harus ada ----------
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host '[X] ffmpeg tidak ditemukan di PATH.' -ForegroundColor Red
  exit 1
}

# ---------- Minta path bila belum diberi ----------
if ([string]::IsNullOrWhiteSpace($SourceDir)) {
  $SourceDir = Read-Host '  Direktori sumber (berisi PNG)'
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Read-Host '  Direktori output (JPG)'
}
$SourceDir = $SourceDir.Trim().Trim('"')
$OutDir = $OutDir.Trim().Trim('"')

if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
  Write-Host "[X] Direktori sumber tidak ada: $SourceDir" -ForegroundColor Red
  exit 1
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# ---------- Kumpulkan file ----------
$gci = @{ LiteralPath = $SourceDir; Filter = '*.png'; File = $true }
if ($Recurse) { $gci['Recurse'] = $true }
$files = Get-ChildItem @gci | Sort-Object FullName
$total = $files.Count
if ($total -eq 0) {
  Write-Host '[!] Tidak ada file *.png di direktori sumber.' -ForegroundColor Yellow
  exit 0
}
Write-Host "  Ditemukan $total file PNG. Quality q:v=$Quality." -ForegroundColor Gray
Write-Host ''

# ---------- Loop konversi ----------
$frames = @('|', '/', '-', '\')
$converted = 0; $skipped = 0; $failed = 0
$failedFiles = @()
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$i = 0

foreach ($f in $files) {
  $i++
  $dst = Join-Path $OutDir ($f.BaseName + '.jpg')
  $tag = "[$i/$total]"
  $disp = $f.Name
  if ($disp.Length -gt 55) { $disp = $disp.Substring(0, 52) + '...' }

  if ((Test-Path -LiteralPath $dst) -and (-not $Force)) {
    Write-Host "`r  - $tag SKIP (sudah ada): $disp" -ForegroundColor DarkGray
    $skipped++
    continue
  }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'ffmpeg'
  $psi.Arguments = "-y -loglevel warning -i `"$($f.FullName)`" -q:v $Quality `"$dst`""
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.RedirectStandardError = $true
  $psi.RedirectStandardOutput = $true

  try {
    $p = [System.Diagnostics.Process]::Start($psi)
    $fi = 0
    while (-not $p.HasExited) {
      $ch = $frames[$fi % $frames.Count]; $fi++
      Write-Host "`r  $ch $tag converting: $disp" -NoNewline -ForegroundColor Cyan
      Start-Sleep -Milliseconds 120
    }
    $p.WaitForExit()
    $ok = ($p.ExitCode -eq 0) -and (Test-Path -LiteralPath $dst)
  } catch {
    $ok = $false
  }

  if ($ok) {
    $mb = [math]::Round(((Get-Item -LiteralPath $dst).Length / 1MB), 2)
    Write-Host "`r  + $tag OK (${mb}MB): $disp$(' ' * 10)" -ForegroundColor Green
    $converted++
  } else {
    Write-Host "`r  X $tag GAGAL: $disp$(' ' * 10)" -ForegroundColor Red
    $failed++
    $failedFiles += $f.FullName
  }
}
$sw.Stop()

# ---------- Ringkasan ----------
$elapsed = '{0:mm\:ss}' -f $sw.Elapsed
$bar = '+' + ('=' * 44) + '+'
Write-Host ''
Write-Host $bar -ForegroundColor Cyan
Write-Host ('|  CONVERT SUMMARY' + (' ' * 25) + '|') -ForegroundColor Cyan
Write-Host $bar -ForegroundColor Cyan
Write-Host ('|  Total     : {0,-29}|' -f $total)
Write-Host ('|  Converted : {0,-29}|' -f $converted) -ForegroundColor Green
Write-Host ('|  Skipped   : {0,-29}|' -f $skipped) -ForegroundColor Gray
if ($failed -gt 0) {
  Write-Host ('|  Failed    : {0,-29}|' -f $failed) -ForegroundColor Red
} else {
  Write-Host ('|  Failed    : {0,-29}|' -f $failed)
}
Write-Host ('|  Durasi    : {0,-29}|' -f $elapsed)
Write-Host ('|  Output    : {0,-29}|' -f $OutDir)
Write-Host $bar -ForegroundColor Cyan
if ($failedFiles.Count -gt 0) {
  Write-Host '  File gagal:' -ForegroundColor Red
  $failedFiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
  exit 1
}

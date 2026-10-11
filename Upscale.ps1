<#
.SYNOPSIS
  Upscale semua image dalam satu folder memakai Upscayl CLI (model standard).

.DESCRIPTION
  Meminta folder input (source), folder output, dan skala (default 2x),
  lalu memproses semua *.png / *.jpg / *.jpeg / *.webp dengan:
    upscayl-standard-4x -z 4 -s <scale>
  Melewati file yang sudah ada di folder output. Folder output dibuat
  otomatis bila belum ada; bila sudah berisi file, muncul peringatan
  konfirmasi (lewati dengan -Force).

  Workaround batas MAX_PATH 260 karakter milik upscayl-bin.exe: setiap file
  disalin dulu ke nama pendek di TEMP, diproses di sana, hasilnya disalin
  kembali dengan nama asli.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Upscale.ps1
  .\Upscale.ps1 -InputDir "D:\src" -OutputDir "D:\upscaled" -Scale 5
  .\Upscale.ps1 -InputDir "D:\src" -OutputDir "D:\upscaled" -Force
#>
param(
  [string]$InputDir = "",
  [string]$OutputDir = "",
  [string]$Model = "upscayl-standard-4x",
  [int]$Scale = 2,
  [switch]$Force
)

$Bin       = "C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe"
$ModelsDir = "C:\Program Files\Upscayl\resources\models"
$TmpDir    = "C:\Users\alama\AppData\Local\Temp\opencode"
$TmpIn     = Join-Path $TmpDir "u_in.png"
$TmpOut    = Join-Path $TmpDir "u_out.png"
$LogFile   = Join-Path $TmpDir ("upscayl_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

$SpinFrames = @('|', '/', '-', '\')

function Show-Banner($ScaleLabel) {
  Write-Host ""
  Write-Host "   _   _ ____  ____   ____    _    _     _____" -ForegroundColor Cyan
  Write-Host "  | | | |  _ \/ ___| / ___|  / \  | |   | ____|" -ForegroundColor Cyan
  Write-Host "  | | | | |_) \___ \| |     / _ \ | |   |  _|" -ForegroundColor Cyan
  Write-Host "  | |_| |  __/ ___) | |___ / ___ \| |___| |___" -ForegroundColor Cyan
  Write-Host "   \___/|_|   |____/ \____/_/   \_\_____|_____|" -ForegroundColor Cyan
  Write-Host ("              UPSCALE {0}X image upscaler (Upscayl CLI)" -f $ScaleLabel) -ForegroundColor Yellow
  Write-Host ""
}

function Read-Folder($Prompt) {
  while ($true) {
    $v = (Read-Host $Prompt).Trim().Trim('"').Trim("'")
    if ($v -ne "" -and (Test-Path -LiteralPath $v -PathType Container)) { return (Get-Item -LiteralPath $v).FullName }
    Write-Host "  Folder tidak ditemukan, coba lagi." -ForegroundColor Red
  }
}

function Show-Bar($Done, $Total, $Width = 30) {
  if ($Total -eq 0) { $Total = 1 }
  $pct  = [int]($Done * 100 / $Total)
  $fill = [int]($Done * $Width / $Total)
  return ("[" + ("#" * $fill) + ("-" * ($Width - $fill)) + "] $pct%")
}

function Format-Size($Bytes) {
  if ($Bytes -ge 1GB) { return ("{0:N2} GB" -f ($Bytes / 1GB)) }
  if ($Bytes -ge 1MB) { return ("{0:N1} MB" -f ($Bytes / 1MB)) }
  return ("{0:N0} KB" -f ($Bytes / 1KB))
}

$script:ffprobeOk = [bool](Get-Command ffprobe -ErrorAction SilentlyContinue)
function Test-ImageComplete($Path) {
  # True bila penanda akhir file utuh (magic via ISI, bukan ekstensi -
  # output Upscayl bernama .jpg tapi isinya PNG).
  try {
    $fs = [IO.File]::OpenRead($Path)
    $len = $fs.Length
    if ($len -lt 12) { $fs.Close(); return $false }
    $h = New-Object byte[] 12
    [void]$fs.Read($h, 0, 12)
    $isJpg = ($h[0] -eq 0xFF -and $h[1] -eq 0xD8)
    $isPng = ($h[0] -eq 0x89 -and $h[1] -eq 0x50 -and $h[2] -eq 0x4E -and $h[3] -eq 0x47)
    $isWebp = ($h[0] -eq 0x52 -and $h[1] -eq 0x49 -and $h[2] -eq 0x46 -and $h[3] -eq 0x46 -and
               $h[8] -eq 0x57 -and $h[9] -eq 0x45 -and $h[10] -eq 0x42 -and $h[11] -eq 0x50)
    $ok = $false
    if ($isJpg -and $len -ge 2) {
      $fs.Seek(-2, [IO.SeekOrigin]::End) | Out-Null
      $t = New-Object byte[] 2; [void]$fs.Read($t, 0, 2)
      $ok = ($t[0] -eq 0xFF -and $t[1] -eq 0xD9)
    } elseif ($isPng -and $len -ge 8) {
      $fs.Seek(-8, [IO.SeekOrigin]::End) | Out-Null
      $t = New-Object byte[] 8; [void]$fs.Read($t, 0, 8)
      $ok = ($t[0] -eq 0x49 -and $t[1] -eq 0x45 -and $t[2] -eq 0x4E -and $t[3] -eq 0x44 -and
             $t[4] -eq 0xAE -and $t[5] -eq 0x42 -and $t[6] -eq 0x60 -and $t[7] -eq 0x82)
    } elseif ($isWebp -and $len -ge 12) {
      $ok = (([BitConverter]::ToUInt32($h, 4) + 8) -eq $len)
    }
    $fs.Close()
    return $ok
  } catch { return $false }
}
function Test-MediaOk($Path) {
  # Fail-open bila ffprobe tak ada: anggap OK (perilaku lama).
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
  if (-not (Test-ImageComplete $Path)) { return $false }
  if (-not $script:ffprobeOk) { return $true }
  & ffprobe -v error -select_streams v:0 -show_entries stream=codec_name `
    -of default=nw=1:nk=1 -- "$Path" 2>$null | Out-Null
  return ($LASTEXITCODE -eq 0)
}

# ---------- validasi environment ----------
if (-not (Test-Path -LiteralPath $Bin))       { Write-Host "upscayl-bin.exe tidak ditemukan: $Bin" -ForegroundColor Red; exit 1 }
if (-not (Test-Path -LiteralPath $ModelsDir)) { Write-Host "Folder model tidak ditemukan: $ModelsDir" -ForegroundColor Red; exit 1 }
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

# ---------- skala ----------
if (-not $PSBoundParameters.ContainsKey('Scale')) {
  Write-Host "  Catatan: scale 4-5 terverifikasi; 2-3 documented tapi belum diuji di mesin ini." -ForegroundColor DarkGray
  while ($true) {
    $ans = (Read-Host "Scale multiplier [2/3/4/5, default=2]").Trim()
    if ($ans -eq "") { $Scale = 2; break }
    if ($ans -match '^[2-5]$') { $Scale = [int]$ans; break }
    Write-Host "  Skala harus 2, 3, 4, atau 5." -ForegroundColor Red
  }
} elseif ($Scale -lt 2 -or $Scale -gt 5) {
  Write-Host "Scale harus 2..5." -ForegroundColor Red; exit 1
}

Show-Banner $Scale

if ([string]::IsNullOrWhiteSpace($InputDir) -or -not (Test-Path -LiteralPath $InputDir -PathType Container)) {
  $InputDir = Read-Folder "Folder INPUT (berisi source image)"
} else {
  $InputDir = (Get-Item -LiteralPath $InputDir.Trim().Trim('"')).FullName
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $OutputDir = (Read-Host "Folder OUTPUT (hasil upscale, dibuat otomatis bila belum ada)").Trim().Trim('"').Trim("'")
  if ([string]::IsNullOrWhiteSpace($OutputDir)) { Write-Host "  Folder output wajib diisi." -ForegroundColor Red; exit 1 }
}
$OutputDir = $OutputDir.Trim().Trim('"').Trim("'")
if ((Test-Path -LiteralPath $OutputDir) -and -not (Test-Path -LiteralPath $OutputDir -PathType Container)) {
  Write-Host "  Path output adalah file, bukan folder." -ForegroundColor Red; exit 1
}
if (-not (Test-Path -LiteralPath $OutputDir -PathType Container)) {
  New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
  Write-Host "  Folder output dibuat: $OutputDir" -ForegroundColor Green
}
$OutputDir = (Get-Item -LiteralPath $OutputDir).FullName
$existing = @(Get-ChildItem -LiteralPath $OutputDir -File)
if ($existing.Count -gt 0 -and -not $Force) {
  Write-Host ("  PERINGATAN: folder output sudah berisi {0} file." -f $existing.Count) -ForegroundColor Yellow
  $existing | Select-Object -First 3 | ForEach-Object { Write-Host ("    - {0}" -f $_.Name) -ForegroundColor DarkGray }
  if ([Console]::IsInputRedirected) {
    Write-Host "  Mode non-interaktif: tambahkan -Force untuk lanjut." -ForegroundColor Red; exit 1
  }
  $confirm = (Read-Host "  Lanjut? [y/N]").Trim().ToLower()
  if ($confirm -ne "y" -and $confirm -ne "ya") { Write-Host "  Dibatalkan." -ForegroundColor Yellow; exit 0 }
}
if ($InputDir -eq $OutputDir) { Write-Host "Folder input dan output tidak boleh sama (hindari menimpa source)." -ForegroundColor Red; exit 1 }

$files = Get-ChildItem -LiteralPath $InputDir -File |
  Where-Object { $_.Extension -match '^\.(png|jpe?g|webp)$' } |
  Sort-Object Name

Write-Host ""
Write-Host "  Model   : $Model  (-z 4 -s $Scale)" -ForegroundColor Gray
Write-Host "  Input   : $InputDir" -ForegroundColor Gray
Write-Host "  Output  : $OutputDir" -ForegroundColor Gray
Write-Host "  File    : $($files.Count) image ditemukan" -ForegroundColor Gray
Write-Host "  Log     : $LogFile" -ForegroundColor Gray
if ($files.Count -eq 0) { Write-Host "  Tidak ada image untuk diproses." -ForegroundColor Yellow; exit 0 }

Remove-Item $TmpIn, $TmpOut -Force -ErrorAction SilentlyContinue
"Upscale-${Scale}x mulai: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | input=$InputDir output=$OutputDir" | Out-File $LogFile

# ---------- proses ----------
$total = $files.Count
$done = 0; $ok = 0; $skipped = 0; $failed = 0
$totalStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

for ($idx = 0; $idx -lt $total; $idx++) {
  $f = $files[$idx]
  $dest = Join-Path $OutputDir $f.Name
  $num = "[{0}/{1}]" -f ($idx + 1), $total

  $exists = Test-Path -LiteralPath $dest
  if ($exists -and (-not $Force) -and (Test-MediaOk $dest)) {
    Write-Host "$num SKIP  $($f.Name) (sudah ada)  $(Show-Bar $done $total)" -ForegroundColor DarkGray
    $skipped++; $done++
    continue
  }
  if ($exists -and (-not $Force)) {
    Write-Host "$num RUSAK (proses ulang): $($f.Name)" -ForegroundColor Yellow
  }

  Write-Host "$num PROSES $($f.Name) ($(Format-Size $f.Length))" -ForegroundColor White
  $fileStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
  $fileLog = Join-Path $TmpDir "u_last.log"

  try {
    Copy-Item -LiteralPath $f.FullName -Destination $TmpIn -Force

    $job = Start-Job -ScriptBlock {
      param($b, $i, $o, $m, $n, $s, $log)
      & $b -i $i -o $o -m $m -n $n -z 4 -s $s -f png > $log 2>&1
      $LASTEXITCODE
    } -ArgumentList @($Bin, $TmpIn, $TmpOut, $ModelsDir, $Model, $Scale, $fileLog)

    $si = 0
    while ($job.State -eq 'Running') {
      $el = $fileStopwatch.Elapsed.ToString('mm\:ss')
      Write-Host "`r   $($SpinFrames[$si]) mengolah... $el " -NoNewline -ForegroundColor Cyan
      $si = ($si + 1) % $SpinFrames.Count
      Start-Sleep -Milliseconds 150
    }
    $code = Receive-Job $job
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    if ($fileLog -and (Test-Path -LiteralPath $fileLog)) { Get-Content -LiteralPath $fileLog | Out-File $LogFile -Append }
    $code = @($code)[-1]

    if ($code -eq 0 -and (Test-Path $TmpOut)) {
      # Salin via file sementara + pindah atomis agar interupsi
      # tidak meninggalkan hasil setengah-jadi.
      $tmpDest = "$dest.tmp"
      Copy-Item $TmpOut -Destination $tmpDest -Force
      Move-Item -LiteralPath $tmpDest -Destination $dest -Force
      Remove-Item -LiteralPath $tmpDest -Force -ErrorAction SilentlyContinue
      $outSize = (Get-Item -LiteralPath $dest).Length
      $dur = $fileStopwatch.Elapsed.ToString('mm\:ss')
      Write-Host "`r   OK ${dur}  $(Format-Size $f.Length) -> $(Format-Size $outSize)      " -ForegroundColor Green
      "OK: $($f.Name)" | Out-File $LogFile -Append
      $ok++
    } else {
      Write-Host "`r   GAGAL (exit=$code, lihat log)                                        " -ForegroundColor Red
      "GAGAL: $($f.Name) exit=$code" | Out-File $LogFile -Append
      $failed++
    }
  } catch {
    Write-Host "`r   GAGAL: $($_.Exception.Message)                                        " -ForegroundColor Red
    "GAGAL: $($f.Name) $($_.Exception.Message)" | Out-File $LogFile -Append
    $failed++
  } finally {
    Remove-Item $TmpIn, $TmpOut -Force -ErrorAction SilentlyContinue
  }
  $done++
  Write-Host "   $(Show-Bar $done $total)" -ForegroundColor DarkGray
}

$totalStopwatch.Stop()

# ---------- summary ----------
Write-Host ""
Write-Host "  +==========================================+" -ForegroundColor Yellow
Write-Host "  |  S U M M A R Y                          |" -ForegroundColor Yellow
Write-Host "  +==========================================+" -ForegroundColor Yellow
Write-Host ("   Total file    : {0}" -f $total)
Write-Host ("   Skala         : {0}x" -f $Scale)
Write-Host ("   Berhasil      : {0}" -f $ok) -ForegroundColor Green
Write-Host ("   Skip (ada)    : {0}" -f $skipped) -ForegroundColor DarkGray
if ($failed -gt 0) { Write-Host ("   Gagal         : {0}" -f $failed) -ForegroundColor Red }
else               { Write-Host ("   Gagal         : {0}" -f $failed) }
Write-Host ("   Total waktu   : {0}" -f $totalStopwatch.Elapsed.ToString('hh\:mm\:ss'))
Write-Host ("   Output        : {0}" -f $OutputDir)
Write-Host ("   Log           : {0}" -f $LogFile)
Write-Host "  +==========================================+" -ForegroundColor Yellow
"Upscale-${Scale}x selesai: ok=$ok skip=$skipped fail=$failed waktu=$($totalStopwatch.Elapsed)" | Out-File $LogFile -Append
if ((($ok + $skipped) -eq 0) -and ($total -gt 0)) { exit 1 }
exit 0

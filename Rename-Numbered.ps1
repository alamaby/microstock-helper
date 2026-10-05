<#
.SYNOPSIS
  Rename file dengan penomoran 3 digit (001_, 002_, ...) berdasar umur file.

.DESCRIPTION
  Meminta direktori (bila -Directory tidak diisi), lalu mengurutkan semua
  file di folder itu dari paling lama ke paling baru berdasar CreationTime,
  dan me-rename menjadi "<NNN>_<nama-asli>":
    paling lama -> 001_nama.jpg, berikutnya 002_nama.jpg, dst.

  - Hanya file langsung di folder (tidak recursive).
  - Prefix lama "<NNN>_" dikupas dulu agar re-run idempoten
    (tidak menjadi 001_001_nama.jpg).
  - Rename dua tahap (via nama sementara GUID) agar aman dari tabrakan
    nama selama proses.
  - Mendukung >999 file (otomatis jadi 1000, 1001, ...).

.EXAMPLE
  .\Rename-Numbered.ps1
  .\Rename-Numbered.ps1 -Directory "D:\foto" -DryRun
  .\Rename-Numbered.ps1 -Directory "D:\foto" -Force
#>
param(
  [string]$Directory = "",
  [switch]$DryRun,
  [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ____  _____ _   _    _    __  __ _____ " -ForegroundColor Cyan
Write-Host " |  _ \| ____| \ | |  / \  |  \/  | ____|" -ForegroundColor Cyan
Write-Host " | |_) |  _| |  \| | / _ \ | |\/| |  _|  " -ForegroundColor Cyan
Write-Host " |  _ <| |___| |\  |/ ___ \| |  | | |___ " -ForegroundColor Cyan
Write-Host " |_| \_\_____|_| \_/_/   \_\_|  |_|_____|" -ForegroundColor Cyan
Write-Host "        NUMBERED RENAME (001_... by CreationTime)" -ForegroundColor Yellow
Write-Host ""

function Read-Folder($Prompt) {
  while ($true) {
    $v = (Read-Host $Prompt).Trim().Trim('"').Trim("'")
    if ($v -ne "" -and (Test-Path -LiteralPath $v -PathType Container)) {
      return (Get-Item -LiteralPath $v).FullName
    }
    Write-Host "  Folder tidak ditemukan, coba lagi." -ForegroundColor Red
  }
}

if ([string]::IsNullOrWhiteSpace($Directory) -or -not (Test-Path -LiteralPath $Directory -PathType Container)) {
  if (-not [string]::IsNullOrWhiteSpace($Directory)) {
    Write-Host "  Folder tidak ditemukan: $Directory" -ForegroundColor Yellow
  }
  $Directory = Read-Folder "Masukkan direktori"
} else {
  $Directory = (Get-Item -LiteralPath $Directory.Trim().Trim('"').Trim("'")).FullName
}

$files = @(Get-ChildItem -LiteralPath $Directory -File |
  Sort-Object CreationTime, Name)

if ($files.Count -eq 0) {
  Write-Host "  Tidak ada file di: $Directory" -ForegroundColor Yellow
  exit 0
}

# Susun rencana rename: kupas prefix NNN_ lama agar idempoten.
$plan = @()
for ($i = 0; $i -lt $files.Count; $i++) {
  $f = $files[$i]
  $num = "{0:D3}" -f ($i + 1)
  $base = $f.Name -replace '^\d{3}_', ''
  $newName = "${num}_${base}"
  $plan += [pscustomobject]@{
    No      = $i + 1
    Old     = $f.Name
    New     = $newName
    Created = $f.CreationTime
    Full    = $f.FullName
    Same    = ($f.Name -ceq $newName)
  }
}

Write-Host "  Direktori : $Directory" -ForegroundColor Gray
Write-Host "  File      : $($files.Count) (urut CreationTime, paling lama = 001)" -ForegroundColor Gray
if ($DryRun) { Write-Host "  *** DRYRUN - tidak ada file yang diubah ***" -ForegroundColor Cyan }
Write-Host ""
Write-Host "  Pratinjau (10 pertama):" -ForegroundColor Gray
$plan | Select-Object -First 10 | ForEach-Object {
  $mark = if ($_.Same) { "(tetap)" } else { "" }
  Write-Host ("    {0:D3}  {1}  ->  {2} {3}" -f $_.No, $_.Old, $_.New, $mark) -ForegroundColor DarkGray
}
if ($plan.Count -gt 10) {
  Write-Host ("    ... (+{0} lagi)" -f ($plan.Count - 10)) -ForegroundColor DarkGray
}
Write-Host ""

$toChange = @($plan | Where-Object { -not $_.Same })
if ($toChange.Count -eq 0) {
  Write-Host "  Semua file sudah bernomor urut. Tidak ada yang diubah." -ForegroundColor Green
  exit 0
}

# Cek duplikat nama tujuan (mis. nama asli kembar setelah kupas prefix).
$dupes = @($plan.New | Group-Object | Where-Object { $_.Count -gt 1 })
if ($dupes.Count -gt 0) {
  Write-Host "  GAGAL: ada nama tujuan duplikat, rename dibatalkan:" -ForegroundColor Red
  $dupes | ForEach-Object { Write-Host ("    - {0} ({1}x)" -f $_.Name, $_.Count) -ForegroundColor Red }
  exit 1
}

if ($DryRun) { exit 0 }

if (-not $Force) {
  if ([Console]::IsInputRedirected) {
    Write-Host "  Mode non-interaktif: tambahkan -Force untuk lanjut." -ForegroundColor Red
    exit 1
  }
  $confirm = (Read-Host ("  Rename {0} file? [y/N]" -f $toChange.Count)).Trim().ToLower()
  if ($confirm -ne "y" -and $confirm -ne "ya") {
    Write-Host "  Dibatalkan." -ForegroundColor Yellow
    exit 0
  }
}

# Tahap 1: pindahkan ke nama sementara unik (hindari tabrakan).
$tmpNames = @()
foreach ($p in $plan) {
  $tmp = Join-Path $Directory ([Guid]::NewGuid().ToString("N") + ".renametmp")
  Move-Item -LiteralPath $p.Full -Destination $tmp -Force
  $tmpNames += [pscustomobject]@{ Tmp = $tmp; New = $p.New; Old = $p.Old }
}

# Tahap 2: nama sementara -> nama final bernomor.
$ok = 0; $fail = 0
foreach ($t in $tmpNames) {
  $dest = Join-Path $Directory $t.New
  try {
    Move-Item -LiteralPath $t.Tmp -Destination $dest -Force
    Write-Host ("  OK  {0} -> {1}" -f $t.Old, $t.New) -ForegroundColor Green
    $ok++
  } catch {
    Write-Host ("  GAGAL {0} -> {1} : {2}" -f $t.Old, $t.New, $_.Exception.Message) -ForegroundColor Red
    $fail++
  }
}

Write-Host ""
if ($fail -eq 0) {
  Write-Host ("  Selesai: {0} file di-rename." -f $ok) -ForegroundColor Green
} else {
  Write-Host ("  Selesai: {0} OK, {1} gagal. File sementara sisa (.renametmp) perlu dicek manual." -f $ok, $fail) -ForegroundColor Yellow
}

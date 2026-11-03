<#
.SYNOPSIS
  Orkestrasi batch sekali jalan: generate metadata -> convert template ->
  embed ke file (Adobe Stock + Dreamstime).

.DESCRIPTION
  Dari 1 direktori input berisi JPG hi-res tanpa metadata:
    [1/3] microstock-metadata generate  (backend api, prompt v3)
    [2/3] csv_to_embed.py               (template adobe + dreamstime)
    [3/3] Embed-JpgMetadata.ps1         (triple-sync ke for_adobe/for_dreamstime)
  File sumber tidak pernah diubah. Berhenti bila generate gagal total
  (exit 2/3/4); kegagalan sebagian (exit 1) tetap lanjut dengan baris sukses.

.PARAMETER BatchDir
  Direktori berisi file JPG (boleh di root atau subfolder).

.PARAMETER Agency
  both | adobe | dreamstime. Default: both.

.PARAMETER Backend
  Backend generator: api (OpenAI-compatible & Cloudflare).

.PARAMETER Recursive
  Paksa scan rekursif. Default: otomatis --no-recursive bila ada file
  gambar langsung di root (agar run ulang tak memproses for_*/output-*).

.PARAMETER Limit
  Teruskan --limit ke generate (coba batch kecil dulu).

.PARAMETER DryRun
  Tanpa menulis: generate --dry-run + embed -DryRun.

.PARAMETER Yes
  Lewati konfirmasi sebelum embed (default: tanya dulu agar baris
  needs_review sempat diperiksa).

.EXAMPLE
  .\Process-Batch.ps1 C:\Side\Microstock\resubmit_dreamstime_261006_0919
  .\Process-Batch.ps1 .\resubmit_dreamstime_261006_0919 -Agency dreamstime -Limit 3
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)][string]$BatchDir,
  [ValidateSet("both", "adobe", "dreamstime")][string]$Agency = "both",
  [ValidateSet("api")][string]$Backend = "api",
  [switch]$Recursive,
  [int]$Limit = 0,
  [switch]$DryRun,
  [switch]$Yes,
  [switch]$KeepBackup
)

$ErrorActionPreference = "Stop"

Write-Host @"

  ============================================================
   __  __ ___ ____ ____   ___  ____ _____ ___   ____ _  __
  |  \/  |_ _/ ___|  _ \ / _ \/ ___|_   _/ _ \ / ___| |/ /
  | |\/| || | |   | |_) | | | \___ \ | || | | | |   | ' /
  | |  | || | |___|  _ <| |_| |___) || || |_| | |___| . \
  |_|  |_|___\____|_| \_\\___/|____/ |_| \___/ \____|_|\_\
   PROCESS-BATCH v1.0 - generate + convert + embed (1 input dir)
  ============================================================

"@

$BatchDir = (Resolve-Path $BatchDir).Path
$batchName = Split-Path $BatchDir -Leaf
$GenDir = Join-Path $PSScriptRoot "microstock-metadata-generator"
$VenvPy = Join-Path $GenDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { $VenvPy = "python3" }
$OutApi = Join-Path $BatchDir "output-api"
$adobeCsv = Join-Path $BatchDir "${batchName}_metadata_adobe.csv"
$dreamCsv = Join-Path $BatchDir "${batchName}_metadata_dreamstime.csv"

function Step($n, $title) {
  Write-Host ""
  Write-Host "  [$n/3] $title" -ForegroundColor Cyan
  Write-Host "  ------------------------------------------------------------"
}

# ---------- [1/3] generate ----------
Step 1 "GENERATE metadata ($Backend)"
$flat = @(Get-ChildItem $BatchDir -File -Include *.jpg, *.jpeg, *.png, *.webp 2>$null).Count -gt 0
$genCfg = Join-Path $GenDir "config.yaml"
$genArgs = @("generate", $BatchDir, "--output-dir", $OutApi, "--backend", $Backend)
if (Test-Path -LiteralPath $genCfg) { $genArgs += @("--config", $genCfg) }
if (-not $Recursive -and $flat) { $genArgs += "--no-recursive" }
if ($Limit -gt 0) { $genArgs += @("--limit", "$Limit") }
if ($DryRun) { $genArgs += "--dry-run" }
& (Join-Path $GenDir "run.bat") @genArgs
$genExit = $LASTEXITCODE
if ($genExit -notin @(0, 1)) { Write-Host "  (!) generate gagal total (exit $genExit), berhenti." -ForegroundColor Red; exit $genExit }
if ($DryRun) { Write-Host "  (DryRun selesai, tidak ada yang ditulis)"; exit 0 }

# ---------- [2/3] convert ----------
Step 2 "CONVERT ke template Adobe + Dreamstime"
$metaCsv = Join-Path $OutApi "metadata.csv"
if (-not (Test-Path $metaCsv)) { Write-Host "  (!) metadata.csv tidak ada: $metaCsv" -ForegroundColor Red; exit 1 }
& $VenvPy (Join-Path $GenDir "scripts\csv_to_embed.py") --input $metaCsv `
  --adobe-out $adobeCsv --dreamstime-out $dreamCsv
if ($LASTEXITCODE -ne 0) { exit 1 }

$needReview = @(Import-Csv $metaCsv -Encoding UTF8 | Where-Object { $_.needs_review -eq "true" }).Count
Write-Host "  Baris needs_review: $needReview (cek kolom review_reasons bila > 0)" `
  -ForegroundColor $(if ($needReview -gt 0) { "Yellow" } else { "Green" })
if (-not $Yes) {
  $ans = (Read-Host "  Lanjut embed ke file? [Y/n]").Trim().ToLower()
  if ($ans -eq "n") { Write-Host "  Dibatalkan sebelum embed."; exit 0 }
}

# ---------- [3/3] embed ----------
Step 3 "EMBED ke file (sumber tak diubah)"
$targets = @()
if ($Agency -in @("both", "adobe")) { $targets += @($adobeCsv, "${batchName}_for_adobe") }
if ($Agency -in @("both", "dreamstime")) { $targets += @($dreamCsv, "${batchName}_for_dreamstime") }
for ($k = 0; $k -lt $targets.Count; $k += 2) {
  $csv, $suf = $targets[$k], $targets[$k + 1]
  $outDir = Join-Path $BatchDir $suf
  $eb = @{ CsvPath = $csv; JpgDir = $BatchDir; OutDir = $outDir }
  if ($DryRun) { $eb["DryRun"] = $true }
  if ($KeepBackup) { $eb["KeepBackup"] = $true }
  & (Join-Path $PSScriptRoot "Embed-JpgMetadata.ps1") @eb
  if ($LASTEXITCODE -ne 0) { Write-Host "  (!) embed gagal: $suf" -ForegroundColor Red; exit 1 }
  Write-Host "  Upload: $outDir"
}

Write-Host ""
Write-Host "  ____   ___  _   _ _____" -ForegroundColor Green
Write-Host "  |  _ \ / _ \| \ | | ____|  batch '$batchName' selesai." -ForegroundColor Green

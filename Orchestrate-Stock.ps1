<#
.SYNOPSIS
  Orkestrator microstock: dari image hasil generate AI sampai siap upload
  Adobe Stock + Dreamstime (jalur JPG).

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

  Target EPS saat ini stub ("belum tersedia") - struktur disiapkan untuk cabang
  EPS nanti.

.EXAMPLE
  .\Orchestrate-Stock.ps1
  .\Orchestrate-Stock.ps1 -SourceDir "D:\batch1" -Force
  .\Orchestrate-Stock.ps1 -SourceDir "D:\batch1","D:\batch2","D:\batch3" -Force
  (antrean banyak direktori, semua config default, jalan berurutan)
#>
[CmdletBinding()]
param(
  [ValidateSet("JPG", "EPS")][string]$Target = "",
  [string[]]$SourceDir = @(),
  [ValidateRange(2, 5)][int]$Scale = 5,
  [string]$Copyright = "alamaby",
  [string]$Creator = "alamaby",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$BinExif = "C:\Apps\exiftool\exiftool.exe"
$BinUpscayl = "C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe"
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
# Tangkap param terikat di scope skrip (di dalam fungsi $PSBoundParameters milik fungsi itu).
$script:boundKeys = @($PSBoundParameters.Keys)

function Write-Stage($n, $title) {
  Write-Host ""
  Write-Host ("  ===== [TAHAP {0}] {1} =====" -f $n, $title) -ForegroundColor Cyan
}

function Add-Stage($n, $title, $status, $detail) {
  $script:stages += [pscustomobject]@{ No = $n; Tahap = $title; Status = $status; Detail = $detail }
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
  & $File @Arguments | Out-Host
  return $LASTEXITCODE
}

# ---------- Transform: generator CSV -> 2 CSV embed ----------
function ConvertTo-EmbedCsvs($GenCsv, $AdobeCsv, $DreamCsv, $Copyright, $Creator) {
  $rows = Import-Csv $GenCsv -Encoding UTF8 | Where-Object { $_.status -eq "success" }
  $failed = @(Import-Csv $GenCsv -Encoding UTF8 | Where-Object { $_.status -ne "success" }).Count
  $adobe = @(); $dream = @()
  foreach ($r in $rows) {
    $phrases = @($r.keywords -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique)
    if ($phrases.Count -gt 49) { $phrases = $phrases[0..48] }
    $title70 = if ($r.title.Length -gt 70) { $r.title.Substring(0, 70) } else { $r.title }
    $adobe += [pscustomobject]@{
      SourceFile  = $r.filename
      Title       = $title70
      Description = $r.description
      Keywords    = ($phrases -join ", ")
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
  $adobe | Select-Object $cols | Export-Csv $AdobeCsv -Encoding UTF8 -NoTypeInformation
  $dream | Select-Object $cols | Export-Csv $DreamCsv -Encoding UTF8 -NoTypeInformation
  return [pscustomobject]@{ OK = $rows.Count; Failed = $failed }
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
  $metaDir = Join-Path $stock "metadata"
  $rawDir = Join-Path $metaDir "raw"
  $forAdobe = Join-Path $stock "for_adobe"
  $forDream = Join-Path $stock "for_dreamstime"
  foreach ($d in @($stock, $small, $up, $final, $metaDir, $rawDir, $forAdobe, $forDream)) {
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
    Write-Host "   AI image -> siap upload Adobe + Dreamstime (JPG, upscale ${Scale}x)" -ForegroundColor Yellow
    Write-Host "  Sumber : $SourceDir" -ForegroundColor Gray
    Write-Host "  Kerja  : $stock" -ForegroundColor Gray

    $imgExt = @(".png", ".jpg", ".jpeg", ".webp")

    # ---------- TAHAP 0: preflight ----------
    Write-Stage 0 "Preflight"
    $fatal = @()
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { $fatal += "ffmpeg tidak di PATH" }
    if (-not (Test-Path -LiteralPath $BinExif -PathType Leaf)) { $fatal += "ExifTool tidak ada: $BinExif" }
    if (-not (Test-Path -LiteralPath $BinUpscayl -PathType Leaf)) { $fatal += "upscayl-bin.exe tidak ada: $BinUpscayl" }
    $need = @("Rename-Numbered.ps1", "Convert-PngToJpg.ps1", "Convert-WebpToJpg.ps1", "Upscale.ps1", "Embed-JpgMetadata.ps1")
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
    Write-Host "  [OK] semua prasyarat terpenuhi (backend metadata: $MetadataBackend)." -ForegroundColor Green
    Add-Stage 0 "Preflight" "OK" "backend=$MetadataBackend"

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
    $conv = @{ SourceDir = $SourceDir; OutDir = $small }
    if ($Force) { $conv.Force = $true }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Convert-WebpToJpg.ps1") $conv
    if ($code -ne 0) { throw "Convert WEBP gagal (exit $code)." }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Convert-PngToJpg.ps1") $conv
    if ($code -ne 0) { throw "Convert PNG gagal (exit $code)." }
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
    Add-Stage 2 "Convert kecil" "OK" "$nSmall file"
    if ($nSmall -eq 0) { throw "Tidak ada JPG kecil yang dihasilkan." }

    # ---------- TAHAP 3: upscale ----------
    Write-Stage 3 ("Upscale {0}x" -f $Scale)
    $uargs = @{ InputDir = $small; OutputDir = $up; Scale = $Scale }
    if ($Force) { $uargs.Force = $true }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Upscale.ps1") $uargs
    if ($code -ne 0) { throw "Upscale gagal (exit $code)." }
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
    Add-Stage 3 "Upscale" "OK" "$nUp file"
    if ($nUp -eq 0) { throw "Upscale tidak menghasilkan file." }

    # ---------- TAHAP 4: JPG final ----------
    Write-Stage 4 "Convert JPG final"
    $fin = @{ SourceDir = $up; OutDir = $final }
    if ($Force) { $fin.Force = $true }
    $code = Invoke-Child (Join-Path $PSScriptRoot "Convert-PngToJpg.ps1") $fin
    if ($code -ne 0) { throw "Convert final gagal (exit $code)." }
    $nFinal = @(Get-ChildItem -LiteralPath $final -File -Filter "*.jpg").Count
    Write-Host ("  JPG final: {0} file." -f $nFinal) -ForegroundColor Green
    Add-Stage 4 "JPG final" "OK" "$nFinal file"
    if ($nFinal -eq 0) { throw "Tidak ada JPG final." }

    # ---------- TAHAP 5: metadata (dari JPG kecil) ----------
    Write-Stage 5 "Generate metadata (dari JPG kecil)"
    $runBat = Join-Path $GenDir "run.bat"
    $genCmd = "`"$runBat`" generate `"$small`" --output-dir `"$rawDir`" --backend $MetadataBackend"
    Write-Host ("  > {0}" -f $genCmd) -ForegroundColor DarkGray
    cmd /c $genCmd
    if ($LASTEXITCODE -ne 0) { throw "Generate metadata gagal (exit $LASTEXITCODE) - lihat $rawDir\processing.log." }
    $genCsv = Join-Path $rawDir "metadata.csv"
    if (-not (Test-Path -LiteralPath $genCsv)) { throw "metadata.csv tidak ditemukan di $rawDir." }
    $batch = (Get-Item -LiteralPath $SourceDir).Name -replace "[^\w\-]+", "_"
    $adobeCsv = Join-Path $metaDir ($batch + "_metadata_adobe.csv")
    $dreamCsv = Join-Path $metaDir ($batch + "_metadata_dreamstime.csv")
    $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $Copyright $Creator
    Write-Host ("  Metadata: {0} OK, {1} gagal -> {2}" -f $m.OK, $m.Failed, $metaDir) -ForegroundColor Green
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
      $c = if ($s.Status -eq "OK" -or $s.Status -eq "SKIP") { "Green" } else { "Red" }
      Write-Host ("   [{0}] {1,-14} {2,-6} {3}" -f $s.No, $s.Tahap, $s.Status, $s.Detail) -ForegroundColor $c
    }
    Write-Host ("   Total waktu : {0}" -f $script:swTotal.Elapsed.ToString("hh\:mm\:ss"))
    Write-Host ("   Upload Adobe: {0}" -f $forAdobe)
    Write-Host ("   Upload Dream: {0}" -f $forDream)
    Write-Host ("   Log         : {0}" -f (Join-Path $stock "orchestrator.log"))
    Write-Host "  +==========================================+" -ForegroundColor Yellow
    try { Stop-Transcript | Out-Null } catch { }
  }
  $bad = @($script:stages | Where-Object { $_.Status -notin @("OK", "SKIP") })
  $st = if ($bad.Count -eq 0) { "OK" } else { "GAGAL" }
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
      $Target = Select-Option "Target output" @("JPG", "EPS") 0
    } else { $Target = "JPG" }
  }
  $Target = $Target.ToUpper()
  if ($Target -eq "EPS") {
    Write-Host "  Jalur EPS belum tersedia (stub). Hanya JPG yang didukung saat ini." -ForegroundColor Yellow
    exit 0
  }
  if ($Target -ne "JPG") { Write-Host "  Target tidak dikenal: $Target (pilih JPG/EPS)." -ForegroundColor Red; exit 1 }

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

  if ($ask -and $script:boundKeys -notcontains "Scale") {
    $s = (Read-Host "Skala upscale [2-5, Enter=5]").Trim()
    if ($s -match "^[2-5]$") { $Scale = [int]$s }
  }
  if ($ask -and $script:boundKeys -notcontains "Copyright") {
    $Copyright = Ask-Default "Copyright" $Copyright
    $Creator = Ask-Default "Creator" $Creator
  }
  # Backend metadata dikunci ke API (lokal dinonaktifkan - terlalu lambat).
  $MetadataBackend = "api"

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
      $c = if ($r.Status -eq "OK") { "Green" } else { "Red" }
      Write-Host ("   [{0,-5}] {1}" -f $r.Status, $r.Dir) -ForegroundColor $c
    }
    Write-Host ("   Total waktu antrean: {0}" -f $grand.Elapsed.ToString("hh\:mm\:ss"))
    Write-Host "  +==========================================+" -ForegroundColor Yellow
  }
  $failCount = @($results | Where-Object { $_.Status -ne "OK" }).Count
  if ($failCount -gt 0) { exit 1 } else { exit 0 }
}

if ($MyInvocation.InvocationName -ne ".") { Main }

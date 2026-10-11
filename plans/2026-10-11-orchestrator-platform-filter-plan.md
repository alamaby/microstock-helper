# Orchestrator Platform Filter (`-Platforms`) — Implementation Plan

Created: 2026-10-11 12:00:00

## Objective

Menambah opsi `-Platforms` pada `Orchestrate-Stock.ps1` agar hanya platform yang dipilih yang direktori siap-upload-nya dibuat / dibuat ulang (`for_adobe*`, `for_dreamstime*`, `for_vecteezy_*`, `for_pixabay_*`), tanpa mengubah perilaku default (tanpa `-Platforms` = semua platform, sama seperti sekarang). Berlaku untuk ketiga `Target` (JPG/SVG/EPS), resume-aware dan toleran-partial seperti kontrak yang ada.

## Scope

In scope (satu file saja):

- `Orchestrate-Stock.ps1`: blok `param`, helper seleksi baru, prompt interaktif `Main`, gating TAHAP 6 (JPG), gating TAHAP 7V (vektor), ringkasan + return object, teks bantuan (`.SYNOPSIS`/`.DESCRIPTION`/`.EXAMPLE`).

Out of scope (dilarang diubah):

- `Embed-JpgMetadata.ps1`, `Embed-VectorMetadata.ps1`, semua child convert/trace/preview/eps/upscale/rename (`Convert-PngToJpg.ps1`, `Convert-WebpToJpg.ps1`, `Convert-SvgToEps.ps1`, `Upscale.ps1`, `Trace-Svg.ps1`, `Export-VectorPreview.ps1`, `Rename-Numbered.ps1`), `Process-Batch.ps1`.
- `microstock-metadata-generator/**` (termasuk semua `tests/*.py`), `.env*`, `AGENTS.md`, data `_stock/**`, `.memory/**`, file `plans/**` lain.

Pemetaan Target → direktori (jangan diubah, hanya di-gate):

| Target | Adobe | Dreamstime | Vecteezy | Pixabay |
|--------|-------|------------|----------|---------|
| JPG | `_stock/for_adobe` | `_stock/for_dreamstime` | `_stock/for_vecteezy_photo` | `_stock/for_pixabay_photo` |
| SVG | `_stock/for_adobe_svg` | `_stock/for_dreamstime_svg` | n/a (tidak didukung) | `_stock/for_pixabay_svg` |
| EPS | `_stock/for_adobe_eps` | `_stock/for_dreamstime_eps` | `_stock/for_vecteezy_eps` | `_stock/for_pixabay_svg` |

## Milestones

1. M1 — Parameter + normalisasi + prompt (S1).
2. M2 — Gating embed JPG + validasi JPG (S2).
3. M3 — Gating embed vektor + validasi vektor (S3).
4. M4 — Ringkasan + return object + banner (S4).
5. M5 — Teks bantuan + verifikasi penuh (S5–S6).

## Requirement / Finding Traceability

| ID | Finding / Requirement | Sumber | Ditangani langkah |
|----|----------------------|--------|-------------------|
| F1 | Orchestrator selalu meng-embed semua platform per Target; tidak ada opsi selektif | `Orchestrate-Stock.ps1:1106-1113` (JPG 4x embed), `:1305-1322` (vektor 4x embed) | S1, S2, S3 |
| F2 | Semantik rebuild: child embed selalu overwrite (`Copy-Item -Force`), tidak punya `-Force` | `Embed-JpgMetadata.ps1:29-37` (param tanpa Force), `:212-214` (`Copy-Item -Force`); `Embed-VectorMetadata.ps1:27-36`, `:325-326`, `:355` | S1 (Notes), S2, S3 |
| F3 | `-Force` saat ini memaksa tahap hulu (convert/upscale/trace/preview/metadata-reuse), bukan tahap embed | `Orchestrate-Stock.ps1:973`, `:1018-1019`, `:1156`, `:1176`, `:1214-1215`, `:1242-1243`, `:1272-1273` | S1, S2, S3 (pertahankan, jangan kaitkan ke `-Platforms`) |
| F4 | Vecteezy tidak didukung untuk `Target=SVG`; memilih hanya Vecteezy di SVG menghasilkan nihil | `Orchestrate-Stock.ps1:1314-1325` (`if ($vecKind -eq "eps") … else { "Vecteezy vector skip (butuh EPS…)" }`) | S3 |
| F5 | Laporan `validation_vecteezy_pixabay.txt` hanya mencakup subset Vecteezy+Pixabay | `Orchestrate-Stock.ps1:1131-1140`, `:1333-1343`; `Test-UploadReadiness` di `:548-821` (kontrak warn-only, jangan diubah) | S2, S3 |
| F6 | Ringkasan + return object selalu mencetak 4 direktori | `Orchestrate-Stock.ps1:1375-1404` | S4 |
| F7 | `Main` interaktif belum menanyakan platform; mode batch tidak boleh nge-prompt | `Orchestrate-Stock.ps1:1407-1454` (`$ask = $interactive -and -not $batch`, pola `$script:boundKeys -notcontains` di `:1430-1434`) | S1 |
| R1 | Flag baru `-Platforms` subset dari `Adobe,Dreamstime,Vecteezy,Pixabay`, default semua (backward-compat) | Permintaan user 2026-10-11 | S1 |
| R2 | Platform tak dipilih: tidak ditulis, tidak dihapus, tidak divalidasi, tidak dihitung gagal | Permintaan user ("perlu dibuat atau dibuat ulang") | S2, S3, S4 |
| R3 | Berlaku konsisten untuk JPG/SVG/EPS sesuai tabel pemetaan | Perilaku existing `:842-859` | S2, S3, S4 |

## Tasks

- [x] S1 — Tambah `-Platforms` + helper + prompt `Main`.
- [x] S2 — Gating TAHAP 6 embed JPG + validasi JPG.
- [x] S3 — Gating TAHAP 7V embed vektor + validasi vektor.
- [x] S4 — Ringkasan + return object + banner.
- [x] S5 — Teks bantuan `.SYNOPSIS`/`.DESCRIPTION`/`.EXAMPLE`.
- [x] S6 — Verifikasi parser + helper + matriks manual.

## Implementation Steps (atomik, deterministik)

### S1 — Tambah parameter `-Platforms`, helper `Test-PlatformSelected`, normalisasi + prompt di `Main`

- Tujuan langkah: menyediakan satu-satunya titik kebenaran seleksi platform tanpa mengubah tanda tangan fungsi lain.
- Finding/requirement: F1, F3, F7, R1.
- Dependency: tidak ada (langkah pertama; S2–S6 bergantung padanya).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:1-80` (komentar bantuan + `param` + `$script:boundKeys`),
  - `Orchestrate-Stock.ps1:1407-1445` (`function Main`, pola prompt `Scale`/`Copyright`).
- File yang harus diubah: `Orchestrate-Stock.ps1` saja.
- Simbol terkait: blok `param()` (`$Target`, `$SourceDir`, `$Scale`, `$PreviewWidth`, `$Copyright`, `$Creator`, `$Force`); `$script:boundKeys`; `function Main`; helper baru `Test-PlatformSelected`.
- Kondisi implementasi saat ini:
  - `param` di `:49-57` berisi 6 parameter, tanpa `-Platforms`.
  - `$script:boundKeys = @($PSBoundParameters.Keys)` di `:79` sudah menangkap semua key ter-bound (otomatis mencakup key baru, tidak perlu diubah).
  - `Process-Dir` membaca `$Target`/`$Force` dari scope skrip (tidak via argumen); `$Platforms` akan terlihat dengan cara yang sama — tanda tangan `Process-Dir($DirInput,$Idx,$Total)` di `:823` JANGAN diubah.
- Perubahan konkret (lakukan dalam urutan ini):
  1. Di blok `param` (`:49-57`), setelah baris `[string]$Creator = "alamaby",` tambahkan tepat satu baris sebelum `[switch]$Force`:
     ```powershell
     [ValidateSet("Adobe", "Dreamstime", "Vecteezy", "Pixabay")][string[]]$Platforms = @("Adobe", "Dreamstime", "Vecteezy", "Pixabay"),
     ```
     Koma di akhir baris wajib (semua baris param kecuali terakhir memakai koma).
  2. Setelah baris `$script:boundKeys` (`:79`) dan sebelum `function Write-Stage` (`:81`), sisipkan helper baru verbatim:
     ```powershell
     function Test-PlatformSelected([string]$Name) {
       $n = ([string]$Name).Trim().ToLower()
       foreach ($p in @($Platforms)) {
         if (("$p".Trim().ToLower()) -eq $n) { return $true }
       }
       return $false
     }
     ```
  3. Di `function Main`, setelah normalisasi `$Target` (setelah blok `:1416-1417` yang me-`exit 1` untuk target tak dikenal) dan sebelum parsing `$dirList` (`:1420`), sisipkan normalisasi verbatim:
     ```powershell
     $Platforms = @(@($Platforms) | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
     if ($Platforms.Count -eq 0) { $Platforms = @("Adobe", "Dreamstime", "Vecteezy", "Pixabay") }
     $canon = @{ "adobe" = "Adobe"; "dreamstime" = "Dreamstime"; "vecteezy" = "Vecteezy"; "pixabay" = "Pixabay" }
     $Platforms = @($Platforms | ForEach-Object { $canon[("$_".Trim().ToLower())] } | Where-Object { $_ } | Select-Object -Unique)
     if ($Platforms.Count -eq 0) { $Platforms = @("Adobe", "Dreamstime", "Vecteezy", "Pixabay") }
     ```
  4. Di `Main`, setelah blok prompt `Copyright`/`Creator` (`:1434-1437`) dan sebelum baris `$script:MetadataBackend = "api"` (`:1439`), sisipkan prompt interaktif verbatim:
     ```powershell
     if ($ask -and $script:boundKeys -notcontains "Platforms") {
       while ($true) {
         $pAns = (Read-Host "Platform (koma, Enter=semua) [Adobe,Dreamstime,Vecteezy,Pixabay]").Trim()
         if ([string]::IsNullOrWhiteSpace($pAns)) { break }
         $pTry = @($pAns -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
         $pBad = @($pTry | Where-Object { @("adobe", "dreamstime", "vecteezy", "pixabay") -notcontains $_.ToLower() })
         if ($pBad.Count -eq 0 -and $pTry.Count -gt 0) {
           $canon2 = @{ "adobe" = "Adobe"; "dreamstime" = "Dreamstime"; "vecteezy" = "Vecteezy"; "pixabay" = "Pixabay" }
           $Platforms = @($pTry | ForEach-Object { $canon2[$_.ToLower()] } | Select-Object -Unique)
           break
         }
         Write-Host ("  Platform tak dikenal: {0} (pilih subset Adobe,Dreamstime,Vecteezy,Pixabay)." -f ($pBad -join ", ")) -ForegroundColor Red
       }
     }
     ```
     Catatan: `$ask` sudah didefinisikan di `:1428` sebagai `$interactive -and -not $batch`, sehingga mode batch (>1 dir) dan non-interaktif tidak pernah nge-prompt — pertahankan.
- Urutan perubahan di dalam file: param (butir 1) → helper (butir 2) → normalisasi Main (butir 3) → prompt Main (butir 4). Jangan menyentuh logika `Target`/`SourceDir` di antaranya.
- Behavior yang harus dipertahankan:
  - Tanpa `-Platforms`: `$Platforms` = keempat platform (identik dengan perilaku sekarang).
  - `-Force` tidak berubah makna (hanya hulu); `-Platforms` tanpa `-Force` tetap me-reuse tahap hulu via logika skip yang ada dan me-rebuild (overwrite) platform terpilih di tahap embed (karena child memakai `Copy-Item -Force`, F2).
  - `ValidateSet` case-insensitive; nilai tak dikenal dari CLI langsung ditolak PowerShell sebelum `Main` jalan (tidak perlu pesan kustom).
- Error handling / edge case:
  - `-Platforms @()` eksplisit kosong → dinormalisasi ke semua (butir 3), bukan nol platform.
  - Duplikat / campuran case (`adobe,Adobe,ADOBE`) → `Select-Object -Unique` setelah kanonikalisasi.
  - Prompt interaktif salah ketik → loop ulang, tidak `exit`; `Enter` kosong → pertahankan default semua.
  - `Target=SVG` + `Vecteezy` bukan error di S1 (ditangani sebagai warning di S3).
- Test yang harus ditambahkan/diubah: tidak ada harness Pester untuk orchestrator (tidak boleh dibuat di plan ini, lihat OQ-4). Verifikasi via dot-source helper (perintah di bawah), bukan run pipeline penuh.
- Input test dan expected result (di sesi PowerShell terpisah, dari direktori repo, TANPA mengeksekusi pipeline — aman karena file punya guard `if ($MyInvocation.InvocationName -ne ".") { Main }` di `:1475`):
  1. `. .\Orchestrate-Stock.ps1` lalu `Test-PlatformSelected "adobe"` → `$true` (default semua).
  2. `$Platforms = @("Adobe"); Test-PlatformSelected "dreamstime"` → `$false`; `Test-PlatformSelected "ADOBE"` → `$true` (case-insensitive).
  3. `.\Orchestrate-Stock.ps1 -Target JPG -SourceDir .\tidak-ada -Platforms Salah` → error `ValidateSet` sebelum eksekusi (bukan FATAL orchestrator).
- Command verifikasi (read-only, tidak mengubah repo):
  ```powershell
  powershell -NoProfile -NonInteractive -Command "$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Side\Microstock\Orchestrate-Stock.ps1',[ref]$null,[ref]$e); 'errors=' + $e.Count"
  powershell -NoProfile -NonInteractive -Command "(Get-Command 'C:\Side\Microstock\Orchestrate-Stock.ps1').Parameters['Platforms'].ParameterType.Name"
  ```
- Hasil verifikasi yang diharapkan: `errors=0`; tipe parameter `String[]`.
- Completion criteria: (a) parser 0 error; (b) `Get-Command … .Parameters.Keys` memuat `Platforms`; (c) ketiga uji dot-source di atas lolos.
- File/area yang tidak boleh diubah di langkah ini: semua child script, `Test-UploadReadiness`, tahap embed 6/7V, ringkasan/return, `microstock-metadata-generator/**`, `.env*`, `_stock/**`.

### S2 — Gating TAHAP 6 embed JPG (Adobe/Dreamstime/Vecteezy-photo/Pixabay-photo) + validasi JPG

- Tujuan langkah: hanya platform terpilih yang di-embed/divalidasi pada jalur JPG.
- Finding/requirement: F1, F2, F5, R2, R3 (baris JPG tabel pemetaan).
- Dependency: S1 (membutuhkan `$Platforms` + `Test-PlatformSelected`).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:831-860` (variabel `$forAdobeJpg/$forDreamJpg/$forVectPhoto/$forPixPhoto`; loop `New-Item` — JANGAN diubah, lihat OQ-2),
  - `Orchestrate-Stock.ps1:1104-1140` (TAHAP 6 + salin CSV + `Repair-VecteezyPackage` + hitung `$nA/$nD/$nV/$nP` + `$vpPkgs` + `Test-UploadReadiness`).
- File yang harus diubah: `Orchestrate-Stock.ps1` saja (rentang `:1104-1140`).
- Simbol terkait: `Process-Dir`, `Invoke-Child`, `Embed-JpgMetadata.ps1` (dipanggil, tidak diubah), `Repair-VecteezyPackage` (`:149-252`), `Test-UploadReadiness` (`:548-821`, dipanggil, tidak diubah).
- Kondisi implementasi saat ini:
  - `:1106-1113` memanggil 4x `Invoke-Child … Embed-JpgMetadata.ps1` tanpa syarat (Adobe `$adobeCsv`→`$forAdobe`; Dream `$dreamCsv`→`$forDream`; Vect `$vectCsv`→`$forVectPhoto`; Pix `$pixCsv`→`$forPixPhoto`).
  - `:1115-1116` menyalin CSV Vecteezy/Pixabay; `:1118-1122` sanitasi Vecteezy; `:1124-1129` menghitung + mencetak 4 count; `:1131-1134` membangun `$vpPkgs` 2 entri lalu validasi.
- Perubahan konkret (dalam urutan file, pertahankan urutan Adobe→Dream→Vecteezy→Pixabay):
  1. Di awal TAHAP 6 (tepat setelah `Write-Stage 6 …` di `:1105`), sisipkan:
     ```powershell
     $doAdobe = Test-PlatformSelected "Adobe"; $doDream = Test-PlatformSelected "Dreamstime"
     $doVect = Test-PlatformSelected "Vecteezy"; $doPix = Test-PlatformSelected "Pixabay"
     ```
  2. Bungkus tiap `Invoke-Child` `:1106-1113` dengan guard-nya: Adobe dengan `if ($doAdobe) { … }`, Dream dengan `if ($doDream) { … }`, Vecteezy dengan `if ($doVect) { … }`, Pixabay dengan `if ($doPix) { … }`. Pesan `[!] Embed … sebagian gagal` di dalam guard masing-masing tetap sama.
  3. `:1115` (`Copy-Item $vectCsv → $forVectPhoto`) hanya bila `$doVect`; `:1116` hanya bila `$doPix`.
  4. Blok `try { Repair-VecteezyPackage … }` (`:1118-1122`) hanya bila `$doVect`; bila tidak dipilih, ganti dengan `Write-Host "  Vecteezy-photo skip (tak dipilih)." -ForegroundColor Gray`.
  5. Hitung count (`:1124-1127`): tiap baris menjadi kondisional — bila dipilih hitung seperti sekarang, bila tidak set `-1`:
     ```powershell
     $nA = if ($doAdobe) { @(Get-ChildItem -LiteralPath $forAdobe -File -Filter "*.jpg").Count } else { -1 }
     ```
     (analog untuk `$nD/$nV/$nP`). Baris `Write-Host ("  Siap upload: Adobe={0}, …" …)` (`:1128`) diganti format yang mencetak `-` untuk `-1`:
     ```powershell
     $fA = if ($doAdobe) { "$nA" } else { "-" }; $fD = if ($doDream) { "$nD" } else { "-" }
     $fV = if ($doVect) { "$nV" } else { "-" }; $fP = if ($doPix) { "$nP" } else { "-" }
     Write-Host ("  Siap upload: Adobe={0}, Dreamstime={1}, Vecteezy={2}, Pixabay={3}." -f $fA, $fD, $fV, $fP) -ForegroundColor Green
     ```
     dan `Add-Stage 6 "Embed" "OK" "Adobe=$fA, Dreamstime=$fD, Vecteezy=$fV, Pixabay=$fP"`.
  6. `$vpPkgs` (`:1131-1134`): bangun kondisional — mulai `$vpPkgs = @{}`, tambah `"Vecteezy Photo"` hanya bila `$doVect`, `"Pixabay Photo"` hanya bila `$doPix`. Blok `try { $w = Test-UploadReadiness … }` hanya bila `$vpPkgs.Count -gt 0`; bila kosong cetak `Write-Host "  Validasi skip (platform tak dipilih)." -ForegroundColor Gray` dan JANGAN panggil `Test-UploadReadiness` (agar laporan lama tidak tertimpa laporan kosong).
- Urutan perubahan: butir 1 → 2 → 3 → 4 → 5 → 6 (mengikuti urutan file).
- Behavior yang harus dipertahankan:
  - Bila semua dipilih: urutan eksekusi, pesan, CSV, sanitasi, dan validasi identik dengan sekarang (kecuali format count `-` yang tak pernah muncul saat semua dipilih).
  - Metadata CSV di `_stock/metadata/` tetap di-generate penuh 4 file (tahap 5 tidak di-gate — embed yang di-gate).
  - Loop `New-Item` `:857-859` tetap membuat semua direktori (lihat OQ-2) — gating hanya soal penulisan/validasi.
  - Overwrite semantics: embed terpilih menimpa file lama via `Copy-Item -Force` child (F2); direktori tak dipilih tidak disentuh sama sekali (tidak dihapus, tidak ditulis).
- Error handling / edge case:
  - Hanya Vecteezy gagal (exit ≠ 0): pesan `[!] … lanjut` seperti sekarang; tahap tetap `Add-Stage … "OK"` (kontrak partial-tolerance, bukan PARTIAL baru).
  - `$forVectPhoto` berisi file basi dari run lama + Vecteezy tak dipilih → JANGAN bersihkan (prinsip R2); pembersihan basi hanya terjadi di dalam `Repair-VecteezyPackage` saat Vecteezy dipilih.
- Test / input / expected (manual, di SALINAN temp — jangan run di batch repo asli):
  - Fixture: salin satu batch kecil yang sudah punya `_stock/04_final_jpg/*.jpg` + `_stock/metadata/*_metadata_{adobe,dreamstime,vecteezy,pixabay}.csv` ke `C:\Users\alama\AppData\Local\Temp\opencode\platfix\` (melewati API key karena metadata sudah lengkap — tahap 5 tetap jalan `run.bat`; bila API tak tersedia, uji ini ditunda dan ganti dengan uji dot-source S1 + inspeksi kode).
  - Run `-Target JPG -Platforms Adobe` → `for_adobe\*.jpg` timestamp baru, `for_dreamstime\`, `for_vecteezy_photo\`, `for_pixabay_photo\` timestamp lama (tak tersentuh); summary `Adobe=N, Dreamstime=-, Vecteezy=-, Pixabay=-`.
  - Run default (tanpa `-Platforms`) → keempat direktori tersentuh, summary semua angka (regresi backward-compat).
- Command verifikasi: parser S1 + `Select-String -LiteralPath Orchestrate-Stock.ps1 -Pattern 'doAdobe|doDream|doVect|doPix'` mengembalikan >0 hit di rentang TAHAP 6.
- Hasil verifikasi yang diharapkan: parser `errors=0`; guard hadir tepat 4 (satu per platform) di TAHAP 6.
- Completion criteria: (a) semua-dipilih identik perilaku lama; (b) subset hanya menyentuh direktori terpilih; (c) tanpa `-Platforms` tidak ada `skip` semu.
- File/area yang tidak boleh diubah: `Embed-JpgMetadata.ps1`, `ConvertTo-EmbedCsvs`, tahap 5 metadata, `Test-UploadReadiness` itu sendiri, `microstock-metadata-generator/**`.

### S3 — Gating TAHAP 7V embed vektor (Adobe/Dreamstime/Pixabay-SVG/Vecteezy-EPS) + validasi vektor

- Tujuan langkah: hanya platform terpilih yang di-embed/divalidasi pada jalur SVG/EPS, dengan peringatan eksplisit untuk kombinasi tak valid Vecteezy+SVG.
- Finding/requirement: F1, F2, F4, F5, R2, R3 (baris SVG/EPS tabel pemetaan).
- Dependency: S1 (seleksi); independen terhadap S2 (jalur berbeda) tetapi ikuti pola guard yang sama.
- File yang harus dibaca: `Orchestrate-Stock.ps1:1295-1343` (TAHAP 7V + `$staleFilter` cleanup + 4 embed + count + `$vpPkgs`).
- File yang harus diubah: `Orchestrate-Stock.ps1` saja (rentang `:1295-1343`).
- Simbol terkait: `Process-Dir`, `Invoke-Child`, `Embed-VectorMetadata.ps1` (dipanggil, tidak diubah), `$vecSrc/$vecKind/$vecFilter` (`:1264`, `:1292`), `Repair-VecteezyPackage`.
- Kondisi implementasi saat ini:
  - `:1301-1304` menghapus `$staleFilter` di `$forAdobe/$forDream` tanpa syarat.
  - `:1305-1310` embed Adobe-vektor + Dream-vektor; `:1311-1313` embed Pixabay-SVG; `:1314-1325` embed Vecteezy-EPS bila `$vecKind -eq "eps"`, else cetak skip-butuh-EPS.
  - `:1326-1331` hitung 4 count; `:1333-1337` bangun `$vpPkgs` (Vecteezy-EPS kondisional + Pixabay-SVG selalu).
- Perubahan konkret (dalam urutan file):
  1. Tepat setelah `Write-Stage 7 …` (`:1296`), sisipkan sama seperti S2:
     ```powershell
     $doAdobe = Test-PlatformSelected "Adobe"; $doDream = Test-PlatformSelected "Dreamstime"
     $doVect = Test-PlatformSelected "Vecteezy"; $doPix = Test-PlatformSelected "Pixabay"
     ```
     (Variabel lokal tahap; tidak mengganggu S2 karena scope fungsi yang sama namun tahap berbeda —赋值 ulang deterministik.)
  2. Cleanup `:1301-1304`: iterasi hanya direktori terpilih — `if ($doAdobe) { hapus $staleFilter di $forAdobe }`, `if ($doDream) { … $forDream }`. Jangan menambah penghapusan direktori tak dipilih.
  3. `:1305-1307` (Adobe-vektor) bungkus `if ($doAdobe) { … }` else `Write-Host "  Adobe-vektor skip (tak dipilih)." -ForegroundColor Gray`; `:1308-1310` (Dream-vektor) analog.
  4. `:1311-1313` (Pixabay-SVG) bungkus `if ($doPix) { … }` else skip-gray analog.
  5. Blok `:1314-1325` ganti verbatim menjadi:
     ```powershell
     if (-not $doVect) {
       Write-Host "  Vecteezy vector skip (tak dipilih)." -ForegroundColor Gray
     } elseif ($vecKind -eq "eps") {
       $vemb = @{ CsvPath = $vectCsv; JpgDir = $prevDir; VecDir = $epsDir; OutDir = $forVectEps; VecKind = "eps" }
       $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-VectorMetadata.ps1") $vemb
       if ($code -ne 0) { Write-Host "  [!] Embed Vecteezy-EPS sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
       try {
         Repair-VecteezyPackage $forVectEps (Join-Path $forVectEps ((Get-Item $vectCsv).BaseName + ".csv"))
       } catch {
         Write-Host "  [!] Sanitasi Vecteezy-EPS gagal, lanjut." -ForegroundColor Yellow
       }
     } else {
       Write-Host "  Vecteezy diminta tapi Target=SVG tidak mendukung vektor-Vecteezy; skip (jalankan Target=EPS)." -ForegroundColor Yellow
     }
     ```
  6. Count `:1326-1329` kondisional seperti S2 (`-1` bila tak dipilih), pesan `:1330` + `Add-Stage 7` memakai `-` untuk tak dipilih.
  7. `$vpPkgs` (`:1333-1337`): mulai `@{}`; tambah `"Vecteezy EPS"` hanya bila `$doVect -and $vecKind -eq "eps"`; tambah `"Pixabay SVG"` hanya bila `$doPix`. Panggil `Test-UploadReadiness` hanya bila `$vpPkgs.Count -gt 0`, else cetak skip-gray (jangan timpa laporan lama).
- Behavior yang harus dipertahankan: semua-dipilih identik dengan sekarang (termasuk pesan skip-butuh-EPS lama yang kini hanya muncul bila Vecteezy diminta di SVG — redaksinya diperjelas di butir 5); CSV `_stock/metadata/` tetap penuh 4 file (tahap 3V tidak di-gate).
- Error handling / edge case:
  - `-Target SVG -Platforms Vecteezy` → tidak throw, tidak menulis paket apa pun di 7V, mencetak warning kuning butir 5, count semua `-`/0-dipilih, tahap `Add-Stage 7 "Embed vektor" "OK" "Adobe=-, …"` + lanjut ke summary (bukan FATAL). Ini satu-satunya kombinasi yang menghasilkan nol paket — harus eksplisit di summary (lihat S4).
  - `-Target EPS -Platforms Pixabay` → hanya `for_pixabay_svg` (SVG dari `VecDir=$svgDir`, `VecKind="svg"`) yang ditulis; CinEPs tidak disentuh.
- Test / input / expected (salinan temp, bila API tersedia; bila tidak, inspeksi kode + parser):
  - `-Target EPS -Platforms Vecteezy` → hanya `for_vecteezy_eps\*.eps` baru; `for_adobe_eps\`, `for_dreamstime_eps\`, `for_pixabay_svg\` tak tersentuh.
  - `-Target SVG -Platforms Vecteezy` → warning kuning + tidak ada file baru di paket vektor manapun.
  - Default tanpa `-Platforms` di SVG → perilaku lama (Adobe+`Dream+Pixabay, pesan skip Vecteezy).
- Command verifikasi: parser S1 + `Select-String -Pattern 'Vecteezy diminta tapi Target=SVG' Orchestrate-Stock.ps1` tepat 1 hit.
- Hasil verifikasi yang diharapkan: `errors=0`; guard 4 platform hadir di 7V.
- Completion criteria: subset vektor hanya menyentuh direktori terpilih; kombinasi Vecteezy+SVG memberi warning, bukan gagal diam-diam.
- File/area yang tidak boleh diubah: `Embed-VectorMetadata.ps1`, tahap 3V/4V/5V/6V (metadata/trace/preview/EPS), `Test-UploadReadiness`, generator Python.

### S4 — Ringkasan akhir + return object + echo platform di banner

- Tujuan langkah: summary/return jujur mencerminkan subset (tidak menampilkan direktori tak dipilih seolah baru saja dibuat).
- Finding/requirement: F6, R2.
- Dependency: S2, S3 (membutuhkan variabel `$doAdobe/$doDream/$doVect/$doPix` dan count `-1`).
- File yang harus dibaca: `Orchestrate-Stock.ps1:863-891` (banner/resume), `:1346-1404` (finally summary + return).
- File yang harus diubah: `Orchestrate-Stock.ps1` saja.
- Simbol terkait: `Process-Dir` (blok `finally`), `$forAdobe/$forDream/$forVectPhoto/$forPixPhoto/$forVectEps/$forPixSvg/$vectOut/$pixOut`.
- Kondisi implementasi saat ini:
  - `:873` mencetak `AI image -> siap upload Adobe + Dreamstime (Target: $Target)` statis.
  - `:1375-1386` mencetak 4 baris upload tanpa syarat per Target; `:1394-1403` membangun return dengan `$vectOut/$pixOut` peta Target.
- Perubahan konkret:
  1. `:873` ganti menjadi:
     ```powershell
     Write-Host ("   AI image -> siap upload ({0}) (Target: {1})" -f ($Platforms -join ", "), $Target) -ForegroundColor Yellow
     ```
  2. Setelah baris `:875` (`Kerja : $stock`), sisipkan:
     ```powershell
     Write-Host ("  Platform: {0}" -f ($Platforms -join ", ")) -ForegroundColor Gray
     ```
  3. Blok `:1375-1386` ganti setiap baris upload menjadi kondisional dengan helper lokal `$up = { param($sel,$dir) if ($sel) { $dir } else { "(skip - tak dipilih)" } }` atau `if/else` eksplisit per Target:
     - JPG: Adobe→`$forAdobe` bila `$doAdobe` else `(skip…)`; Dream analog; Vecteezy→`$forVectPhoto`; Pixabay→`$forPixPhoto`.
     - SVG: Adobe/Dream analog; `Upload Vecteezy: (n/a - butuh Target=EPS)` bila `$vecKind -ne "eps"` DAN `$doVect`, `(skip - tak dipilih)` bila `-not $doVect`; Pixabay→`$forPixSvg` bila `$doPix`.
     - EPS: keempat direktori kondisional masing-masing.
     Variabel `$do*` harus dihitung ulang di `finally` bila scope tahap tidak menjamin (tahap 6/7V berada di `try`, `finally` tetap satu fungsi — variabel `$do*` masih terlihat; tetapi tugaskan ulang di awal `finally` via `Test-PlatformSelected` agar deterministik bila `try` throw sebelum tahap embed).
  4. Return `:1394-1403`: `$vectOut`/`$pixOut` menjadi `"-"` bila platform tak dipilih:
     ```powershell
     $vectOut = if (-not (Test-PlatformSelected "Vecteezy")) { "-" } elseif ($Target -eq "JPG") { $forVectPhoto } elseif ($Target -eq "EPS") { $forVectEps } else { "-" }
     $pixOut = if (-not (Test-PlatformSelected "Pixabay")) { "-" } elseif ($Target -eq "JPG") { $forPixPhoto } else { $forPixSvg }
     $adobeOut = if (Test-PlatformSelected "Adobe") { $forAdobe } else { "-" }
     $dreamOut = if (Test-PlatformSelected "Dreamstime") { $forDream } else { "-" }
     ```
     dan `Adobe = $adobeOut; Dream = $dreamOut` (ganti `$forAdobe/$forDream` langsung).
- Behavior yang harus dipertahankan: status agregat (`OK`/`PARTIAL`/`GAGAL` dari `$script:stages`, `:1391-1393`) tidak berubah; platform tak dipilih tidak boleh membuat tahap `FATAL`/`PARTIAL` baru.
- Error handling / edge case: `try` throw sebelum embed (mis. upscale gagal) → `finally` tetap mencetak `(skip)` yang benar karena hitung ulang seleksi, bukan mengandalkan variabel tahap.
- Test / input / expected:
  - `-Target JPG -Platforms Pixabay` (pada salinan temp) → summary mencetak `Upload Adobe: (skip - tak dipilih)`, `Upload Pixabay: <dir>`; return object `Adobe="-"`, `Pixabay=<dir>`.
  - Rekap antrean multi-dir (`:1457-1470`) tidak berubah (hanya `Dir`+`Status`).
- Command verifikasi: parser S1 + `Select-String -Pattern 'skip - tak dipilih' Orchestrate-Stock.ps1` ≥ 3 hit.
- Hasil verifikasi yang diharapkan: `errors=0`; tidak ada baris summary yang mencetak direktori tak dipilih sebagai hasil baru.
- Completion criteria: subset tercermin di summary + return; semua-dipilih identik dengan format lama kecuali tambahan baris `Platform:`.
- File/area yang tidak boleh diubah: logika status agregat, `Start/Stop-Transcript`, CSV, validasi.

### S5 — Teks bantuan (`.SYNOPSIS`/`.DESCRIPTION`/`.EXAMPLE`)

- Tujuan langkah: mendokumentasikan flag agar model kecil berikutnya dan user memakai sintaks yang benar tanpa menebak.
- Finding/requirement: R1 (keterbacaan CLI).
- Dependency: S1–S4 (teks harus cocok dengan implementasi final).
- File yang harus dibaca: `Orchestrate-Stock.ps1:1-47`.
- File yang harus diubah: `Orchestrate-Stock.ps1` komentar bantuan saja (tidak ada logika).
- Perubahan konkret (sisipkan, jangan hapus contoh lama):
  - Di `.DESCRIPTION`, setelah deskripsi tahap 6/7V, tambahkan:
    ```
    Opsi -Platforms (subset Adobe,Dreamstime,Vecteezy,Pixabay; default semua):
      hanya platform terpilih yang paket upload-nya ditulis/divalidasi;
      yang tak dipilih dibiarkan utuh (tidak dihapus). Memilih platform =
      membuat ulang (overwrite) paket itu karena child memakai Copy-Item -Force.
      -Force tetap hanya memaksa tahap hulu (convert/upscale/trace/metadata).
      Vecteezy tidak didukung untuk Target=SVG (warning, bukan error).
    ```
  - Di `.EXAMPLE`, tambahkan dua baris:
    ```
    .\Orchestrate-Stock.ps1 -Target JPG -SourceDir "D:\batch1" -Platforms Adobe,Dreamstime
    .\Orchestrate-Stock.ps1 -Target EPS -SourceDir "D:\batch1" -Platforms Vecteezy -Force
    ```
- Behavior: tidak ada (komentar saja).
- Error/edge: tidak ada; pastikan `Get-Help` tetap parse (komentar well-formed).
- Test: `powershell -NoProfile -NonInteractive -Command "(Get-Help 'C:\Side\Microstock\Orchestrate-Stock.ps1').examples"` memuat `Platforms`.
- Completion criteria: contoh baru tampil di `Get-Help`; tidak ada contoh lama yang hilang.
- Jangan ubah: logika apa pun di langkah ini.

### S6 — Verifikasi akhir + matriks regresi manual

- Tujuan langkah: membuktikan tidak ada regresi dan setiap finding punya bukti verifikasi.
- Dependency: S1–S5.
- File yang harus dibaca: semua diff S1–S5 (`git diff -- Orchestrate-Stock.ps1` — read-only, diizinkan karena tidak mengubah repo).
- File yang harus diubah: tidak ada (langkah verifikasi saja).
- Perintah (semua read-only kecuali run manual di salinan TEMP):
  1. `powershell … ParseFile …` → `errors=0`.
  2. `(Get-Command '…Orchestrate-Stock.ps1').Parameters.Keys` memuat `Platforms`.
  3. Uji dot-source S1 (3 kasus) lolos.
  4. Matriks manual (pada salinan di `C:\Users\alama\AppData\Local\Temp\opencode\`, bukan batch repo): JPG-Adobe-saja, JPG-default-semua, EPS-Vecteezy-saja, SVG-Vecteezy-saja (warning), SVG-default, Pixabay-saja. Kriteria: direktori tak dipilih timestamp/isi tak berubah (bandingkan via `Get-ChildItem … | Sort-Object Name,Length` sebelum/sesudah); summary memakai `-`/`(skip)` yang benar.
- Hasil yang diharapkan: 6/6 kasus sesuai; tidak ada `failed_*.txt` baru yang disebabkan oleh platform tak dipilih.
- Completion criteria: seluruh completion criteria S1–S5 terpenuhi; `git status --porcelain` hanya menunjukkan `plans/2026-10-11-orchestrator-platform-filter-plan.md` (+ file ini) — tidak ada modifikasi lain yang belum direncanakan.
- Jangan ubah: apa pun di langkah ini.

## Risks

- R1 — Regresi default: lupa guard membuat platform hilang pada run tanpa `-Platforms`. Mitigasi: default = semua + S6 kasus default; pola guard `if ($doX)` dengan `else` hanya pesan, bukan skip tahap hulu.
- R2 — Jebakan Vecteezy+SVG menghasilkan nol paket dan dikira sukses penuh. Mitigasi: warning kuning eksplisit S3 + summary jujur S4.
- R3 — Laporan validasi tertimpa subset dan dibaca sebagai status penuh. Mitigasi: skip pemanggilan saat subset kosong (S2/S3); header laporan tetap mencantumkan Target (existing `:558`) — tidak diperluas di plan ini (lihat OQ-3).
- R4 — `ValidateSet` menolak diam-diam dalam skrip batch non-interaktif bila ada typo (`Adobe, Dream` dengan spasi → elemen `" Dream"` di-trim di normalisasi S1; tetapi typo nama tetap ditolak PowerShell dengan error — perlakukan sebagai fail-fast yang benar, bukan bug).
- R5 — Variabel `$do*` dihitung di `try` lalu dibaca di `finally` setelah throw dini. Mitigasi: hitung ulang di `finally` (S4 butir 3).

## Progress Log

- 2026-10-11 12:00:00 — Plan dibuat (tanpa implementasi). Menunggu eksekusi oleh model build.
- 2026-10-11 22:18:00 — Implementasi selesai penuh (S1–S6). Parameter `-Platforms` ditambahkan, helper `Test-PlatformSelected` dibuat, gating TAHAP 6 (JPG) dan TAHAP 7V (vektor) aktif, summary + return object mencerminkan platform terpilih, dokumentasi `.DESCRIPTION`/`.EXAMPLE` diperbarui, dan matriks 6 kasus verifikasi manual diuji pada fixture sementara di Temp dengan hasil 100% lolos tanpa error.

## Notes

- Standar arsitektur: fitur kecil tanpa perubahan skema/database; tidak ada deviasi Oracle C2M / TM Forum ODA / TOGAF yang perlu dijustifikasi. Tidak ada perubahan struktur DB live.
- Prinsip env: tidak ada secret yang disentuh; verifikasi tidak memerlukan `MICROSTOCK_API_KEY` kecuali run manual tahap-metadata (gunakan fixture metadata yang sudah ada bila key tak tersedia).
- Backward compatibility terkunci: tanpa `-Platforms` perilaku = sekarang. Satu file = satu plan (plan ini); jangan campur dengan plan upscale/metadata lain.
- Contoh pemakaian final:
  ```powershell
  .\Orchestrate-Stock.ps1 -Target JPG -SourceDir .\batch1 -Platforms Adobe,Dreamstime
  .\Orchestrate-Stock.ps1 -Target EPS -SourceDir .\batch1 -Platforms Vecteezy -Force
  ```

## Open Questions / Blockers

| ID | Pertanyaan | Opsi | Risiko | Rekomendasi |
|----|-----------|------|--------|-------------|
| OQ-1 | UX multi-pilih interaktif | (a) `Read-Host` koma (b) menu panah multi-checkbox baru | (b) butuh helper UI baru, risiko fokus/keyboard lebih besar | (a) — dipakai di S1; jangan implement (b) diam-diam |
| OQ-2 | Apakah direktori `for_*` tak dipilih tetap dibuat kosong saat startup (`:857-859`)? | (a) ya, biarkan (b) hanya buat yang dipilih | (b) menghemat mkdir tetapi menyentuh logika resume yang mengasumsikan dir ada | (a) — S2/S3 tidak mengubah loop `New-Item` |
| OQ-3 | Laporan validasi subset menimpa laporan penuh sebelumnya? | (a) timpa dengan subset (b) laporan per-platform | (b) scope creep + ubah konsumen laporan | (a) + jangan panggil saat subset kosong (S2/S3) |
| OQ-4 | Harness Pester untuk orchestrator? | (a) tunda (b) buat baru di plan ini | (b) memperbesar scope tanpa fixture yang disepakati | (a) — verifikasi manual + dot-source saja |

Tidak ada blocker keras — seluruh langkah dapat dijalankan setelah OQ dijawab dengan rekomendasi di atas. Jangan memilih opsi non-rekomendasi secara diam-diam; catat di `## Notes` bila menyimpang.

## Handoff Checklist (untuk model eksekutor kecil)

- [x] Baca `Orchestrate-Stock.ps1:49-80`, `:823-860`, `:1104-1140`, `:1295-1343`, `:1346-1404`, `:1407-1475` sebelum menyentuh apa pun.
- [x] Kerjakan S1 → S2 → S3 → S4 → S5 → S6 berurutan; jangan melompat (S2/S3 butuh helper S1; S4 butuh count S2/S3).
- [x] Setiap selesai satu langkah, jalankan perintah parser S1; berhenti bila `errors≠0`.
- [x] Jangan mengubah file di luar `Orchestrate-Stock.ps1` (khususnya kedua script Embed, child convert/trace, `microstock-metadata-generator/**`, `.env*`, `_stock/**`, `.memory/**`).
- [x] Uji manual hanya di salinan `C:\Users\alama\AppData\Local\Temp\opencode\`; jangan run orchestrator di batch repo asli.
- [x] Bila menemukan perilaku yang bertentangan dengan plan (mis. Embed ternyata skip-bukan-overwrite), STOP dan catat sebagai temuan baru — jangan redesign diam-diam.
- [x] Selesai: `git status --porcelain` hanya boleh menunjukkan perubahan `Orchestrate-Stock.ps1` (+ plan ini); laporkan matriks 6 kasus S6 dengan timestamp bukti.

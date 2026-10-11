# Metadata Partial-Failure Tolerance (Tahap 5 JPG + Tahap 3V)

Created: 2026-10-11 12:00:00

## Objective

Satu file gagal di generator metadata (`EXIT_ITEM_FAILURE=1`, kasus nyata `natal_261006_1543/generated`: 96 sukses + 1 gagal `039_037-...-adu.jpg` `Empty model response`) tidak boleh membuang 96 sukses dan mengosongkan `for_adobe/for_dreamstime/for_vecteezy_photo/for_pixabay_photo`. Tahap metadata harus menoleransi `exit 1` bila ada baris sukses, mencatat `failed_05_metadata.txt` / `failed_03_metadata.txt`, memberi status `PARTIAL`, dan lanjut ke `ConvertTo-EmbedCsvs` + Embed. `exit 2/3/4` tetap `FATAL`.

## Scope

- `Orchestrate-Stock.ps1` Tahap 5 JPG (baris 1069-1087) dan Tahap 3V Tier-3 generate (baris 1159-1175).
- Tidak mengubah `microstock-metadata-generator/**`, kedua script Embed, child convert/upscale/trace/preview/eps, `Process-Batch.ps1`, `Rename-Numbered.ps1`.

## Milestones

1. Bukti baseline dikunci (S0).
2. Toleransi partial Tahap 5 JPG (S1) — risiko tertinggi, dependensi semua verifikasi.
3. Paritas Tahap 3V vektor (S2) — tergantung pola S1.
4. Verifikasi sintaks + kontrak pytest tidak berubah (S3).
5. Fixture offline tanpa biaya API (S4).
6. Recovery data nyata `natal_261006_1543` secara offline (S5).

## Tasks

- [x] S0 — Baseline read-only
- [x] S1 — Toleransi partial Tahap 5 JPG
- [x] S2 — Paritas Tahap 3V vektor
- [x] S3 — Sintaks + pytest kontrak generator
- [x] S4 — Fixture offline deterministik
- [x] S5 — Recovery offline `natal_261006_1543`

## Risks

- R1: Menoleransi semua non-zero menyamarkan error fatal (config/model/output). Mitigasi: hanya `exit 1` + CSV ada + `OK>0` yang lanjut; `exit 2/3/4` atau `OK==0` tetap `throw`.
- R2: `Write-FailedList` memakai `-NoClobber` sehingga rerun meninggalkan file basi. Mitigasi: `Remove-Item` eksplisit sebelum tulis file baru (hanya di kode baru, tidak ubah helper global).
- R3: Rerun penuh memanggil API ulang 97 file (mahal, ~4 jam). Mitigasi: verifikasi S4/S5 offline tanpa API; rerun API penuh bukan prasyarat penyelesaian.

## Progress Log

- 2026-10-11 12:00:00 — Plan dibuat dari `orchestrator.log` (FATAL Tahap 5 exit 1), `processing.log` (Done 97/96/1), `failed_items.json` (039 Empty response), `cli.py:314`, `constants.py:3-7`, dan perbandingan 4 direktori sukses. Belum ada implementasi.
- 2026-10-11 09:12:00 — S0 baseline terverifikasi (97 final jpg, 0 for_adobe, log FATAL exit 1). S1 diimplementasi pada Tahap 5 JPG. S2 diimplementasi pada Tahap 3V Tier-3. S3 lulus sintaks parser PowerShell & 11 test pytest generator. S4 fixture offline deterministik lulus 3 skenario guard & output CSV. S5 recovery offline terverifikasi pada data nyata natal_261006_1543 menghasilkan 96 baris CSV & 96 JPG hasil embed di folder temp tanpa API.

## Notes

- Kontrak generator TIDAK diubah: `constants.py:3-7` (`EXIT_OK=0`, `EXIT_ITEM_FAILURE=1`, `EXIT_CONFIG_ERROR=2`, `EXIT_MODEL_LOAD_ERROR=3`, `EXIT_OUTPUT_ERROR=4`) dan `cli.py:314` (`return EXIT_ITEM_FAILURE if summary["failed"] else EXIT_OK`) dipertahankan. Bukti: `tests/test_cli.py:74-85` (`test_partial_batch_failure_exit_code` mengharapkan `code == 1`).
- Infrastruktur `PARTIAL` sudah ada dan dipakai ulang tanpa perubahan: `Add-Stage` + summary kuning + blok pemulihan `Orchestrate-Stock.ps1:1325-1343` + status akhir `Orchestrate-Stock.ps1:1361-1363`.
- Filter `ConvertTo-EmbedCsvs($OnlyBasenames)` `Orchestrate-Stock.ps1:431-451` sudah ada dan dipakai ulang tanpa perubahan.

---

## Finding → Langkah Traceability

| Finding | Deskripsi | Ditangani | Verifikasi |
|---|---|---|---|
| G1 | Tahap 5 JPG `throw` pada `exit 1` membuang 96 sukses; `for_*` kosong; 04:07:42 terbuang | S1 | S3, S4, S5 |
| G2 | Pola abort identik di Tahap 3V Tier-3 generate (`:1167-1168`) | S2 | S3, S4 |
| G3 | Tidak ada artefak recovery metadata (`failed_05/03_metadata.txt`) | S1, S2 | S4, S5 |
| G4 | Tidak ada pembedaan `exit 1` (partial) vs `exit 2/3/4` (fatal) | S1, S2 | S3, S4 |
| G5 | `PARTIAL` tidak terpakai untuk metadata karena `throw` lebih dulu | S1, S2 | S4 |
| G6 | `Write-FailedList -NoClobber` basi pada rerun | S1, S2 (via `Remove-Item` lokal) | S4 |

---

## S0 — Baseline read-only (tanpa perubahan kode)

- **Tujuan:** Kunci bukti sebelum edit agar implementer kecil tidak perlu analisis ulang.
- **Finding/requirement:** Fondasi G1-G6.
- **Dependency:** Tidak ada.
- **File yang harus dibaca:**
  1. `Orchestrate-Stock.ps1:1069-1087` (Tahap 5 JPG).
  2. `Orchestrate-Stock.ps1:1159-1175` (Tahap 3V Tier-3).
  3. `Orchestrate-Stock.ps1:89-126` (`Write-FailedList`, `Get-MissingBasenames`).
  4. `Orchestrate-Stock.ps1:431-451` (`ConvertTo-EmbedCsvs` filter).
  5. `Orchestrate-Stock.ps1:1325-1343,1361-1363` (summary PARTIAL).
  6. `microstock-metadata-generator/src/microstock_metadata/cli.py:300-314` (ringkasan + return exit).
  7. `microstock-metadata-generator/src/microstock_metadata/constants.py:3-7` (nilai exit).
  8. `microstock-metadata-generator/tests/test_cli.py:74-85` (kontrak exit 1 partial).
  9. `natal_261006_1543/generated/_stock/orchestrator.log` (tail: `[FATAL] Generate metadata gagal (exit 1)`).
  10. `natal_261006_1543/generated/_stock/metadata/raw/processing.log` (tail: `Done: 97 total, 96 ok, 1 failed`).
  11. `natal_261006_1543/generated/_stock/metadata/raw/failed_items.json` (1 item `039_...-adu.jpg`).
- **File yang harus diubah:** TIDAK ADA.
- **Simbol terkait:** `$LASTEXITCODE`, `$genCsv`, `$haveFinal`, `$haveSmall`, `$m.OK`.
- **Kondisi saat ini:** Tahap 5/3V memakai `if ($LASTEXITCODE -ne 0) { throw ... }` tanpa pengecualian partial.
- **Perubahan konkret:** TIDAK ADA. Hanya catat hitungan: `_stock/02_jpg_small=97`, `03_upscaled=97`, `04_final_jpg=97`, `metadata/*.csv=0`, `for_*=0`, `raw/metadata.csv=97 baris (96 success + 1 failed)`.
- **Urutan:** Baca 1-11 berurutan, catat angka di atas.
- **Behavior dipertahankan:** N/A.
- **Error handling/edge:** Jika angka tidak cocok (mis. `04_final_jpg != 97`), hentikan dan catat sebagai temuan baru, jangan lanjut ke S1.
- **Test:** N/A (inspeksi).
- **Input & expected:** N/A.
- **Command verifikasi (read-only, boleh jalan):**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath 'C:\Side\Microstock\natal_261006_1543\generated\_stock\04_final_jpg' -File -Filter '*.jpg' | Measure-Object | Select-Object -ExpandProperty Count; Get-ChildItem -LiteralPath 'C:\Side\Microstock\natal_261006_1543\generated\_stock\for_adobe' -File | Measure-Object | Select-Object -ExpandProperty Count; Select-String -LiteralPath 'C:\Side\Microstock\natal_261006_1543\generated\_stock\orchestrator.log' -Pattern 'FATAL.*Generate metadata' | Select-Object -Last 1"
  ```
- **Hasil diharapkan:** `97`, `0`, satu baris FATAL.
- **Completion criteria:** Angka terkonfirmasi dan ditulis di handoff implementer.
- **Tidak boleh diubah:** File repo mana pun; `_stock` data nyata; `.env*`.

---

## S1 — Toleransi partial Tahap 5 JPG (BUG UTAMA)

- **Tujuan:** `exit 1` + ada sukses → lanjut ke CSV embed + Embed, status `PARTIAL`, tulis `failed_05_metadata.txt`.
- **Finding:** G1, G3, G4, G5, G6.
- **Dependency:** S0.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1:1069-1087` + helper `:89-104` + `ConvertTo-EmbedCsvs :431-451`.
- **File yang harus diubah:** `Orchestrate-Stock.ps1` HANYA baris 1074-1087 (dari `cmd /c $genCmd` sampai `if ($m.OK -eq 0)`).
- **Simbol terkait:** `cmd /c $genCmd`, `$LASTEXITCODE`, `$genCsv`, `$genExit`, `$genOkRows`, `ConvertTo-EmbedCsvs`, `Write-FailedList`, `Add-Stage`, `$haveFinal`, `$stock`, `$rawDir`, `$metaDir`.
- **Kondisi saat ini:**
  ```powershell
  cmd /c $genCmd
  if ($LASTEXITCODE -ne 0) { throw "Generate metadata gagal (exit $LASTEXITCODE) - lihat $rawDir\processing.log." }
  $genCsv = Join-Path $rawDir "metadata.csv"
  if (-not (Test-Path -LiteralPath $genCsv)) { throw "metadata.csv tidak ditemukan di $rawDir." }
  ...
  $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $vectCsv $pixCsv $Copyright $Creator $haveFinal
  Write-Host ("  Metadata: ...") -ForegroundColor Green
  Add-Stage 5 "Metadata" "OK" "$($m.OK) OK, $($m.Failed) gagal"
  if ($m.OK -eq 0) { throw "Tidak ada metadata sukses untuk di-embed." }
  ```
- **Perubahan konkret (ganti blok di atas dengan blok di bawah, urutan persis):**
  ```powershell
  cmd /c $genCmd
  $genExit = $LASTEXITCODE
  $genCsv = Join-Path $rawDir "metadata.csv"
  $genCsvExists = Test-Path -LiteralPath $genCsv -PathType Leaf
  $genOkRows = 0
  if ($genCsvExists) {
    try { $genOkRows = @(Import-Csv -LiteralPath $genCsv -Encoding UTF8 -ErrorAction Stop | Where-Object { $_.status -in @("success","skipped") }).Count } catch { $genOkRows = 0 }
  }
  if (($genExit -ne 0) -and (($genExit -ne 1) -or (-not $genCsvExists) -or ($genOkRows -eq 0))) { throw "Generate metadata gagal (exit $genExit) - lihat $rawDir\processing.log." }
  if (-not $genCsvExists) { throw "metadata.csv tidak ditemukan di $rawDir." }
  if (($genExit -eq 1) -and ($genOkRows -gt 0)) { Write-Host ("  [!] Generate metadata partial (exit 1): {0} sukses, lanjut dengan file sukses." -f $genOkRows) -ForegroundColor Yellow }
  $batch = (Get-Item -LiteralPath $SourceDir).Name -replace "[^\w\-]+", "_"
  $adobeCsv = Join-Path $metaDir ($batch + "_metadata_adobe.csv")
  $dreamCsv = Join-Path $metaDir ($batch + "_metadata_dreamstime.csv")
  $vectCsv = Join-Path $metaDir ($batch + "_metadata_vecteezy.csv")
  $pixCsv = Join-Path $metaDir ($batch + "_metadata_pixabay.csv")
  $haveFinal = @(Get-ChildItem -LiteralPath $final -File -Filter "*.jpg" -ErrorAction SilentlyContinue | ForEach-Object { $_.BaseName })
  $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $vectCsv $pixCsv $Copyright $Creator $haveFinal
  Write-Host ("  Metadata: {0} OK, {1} gagal, {2} tanpa file-output (dilewati), Vecteezy={3}, Pixabay={4} -> {5}" -f $m.OK, $m.Failed, $m.FilteredOut, $m.Vecteezy, $m.Pixabay, $metaDir) -ForegroundColor Green
  $failedMeta = Join-Path $stock "failed_05_metadata.txt"
  Remove-Item -LiteralPath $failedMeta -Force -ErrorAction SilentlyContinue
  try {
    $failedNames = @(Import-Csv -LiteralPath $genCsv -Encoding UTF8 -ErrorAction Stop | Where-Object { $_.status -notin @("success","skipped") } | ForEach-Object { "$($_.filename)" } | Where-Object { $_ } | Sort-Object -Unique)
    if ($failedNames.Count -gt 0) { Write-FailedList $failedMeta $failedNames }
  } catch { Write-Host ("  [!] Gagal menghitung daftar metadata gagal: {0}" -f $_.Exception.Message) -ForegroundColor Yellow }
  if ($genExit -eq 1) { Add-Stage 5 "Metadata" "PARTIAL" "$($m.OK) OK, $($m.Failed) gagal (exit 1, lihat failed_05_metadata.txt)" }
  else { Add-Stage 5 "Metadata" "OK" "$($m.OK) OK, $($m.Failed) gagal" }
  if ($m.OK -eq 0) { throw "Tidak ada metadata sukses untuk di-embed." }
  ```
  Catatan: baris `$batch/$adobeCsv/$dreamCsv/$vectCsv/$pixCsv/$haveFinal/$m/Write-Host` dipertahankan identik, hanya dipindah setelah guard baru. Jangan ubah Tahap 6 embed.
- **Urutan dalam file:** (1) tangkap `$genExit` segera setelah `cmd /c`; (2) hitung `$genOkRows`; (3) guard `throw` baru; (4) warning kuning partial; (5) CSV/filter/embed-call lama; (6) tulis `failed_05_metadata.txt` (dengan `Remove-Item` dulu); (7) `Add-Stage PARTIAL/OK`; (8) `throw` bila `m.OK==0`.
- **Behavior dipertahankan:** Perintah `run.bat generate ... --backend api`, path CSV, filter `$haveFinal` dari `04_final_jpg`, teks `Metadata: ...`, `throw` bila CSV hilang atau `m.OK==0`, seluruh Tahap 6.
- **Error handling/edge:**
  - `exit 0` → jalur identik hari ini (`OK`).
  - `exit 1` + CSV ada + `OK>0` → `PARTIAL` lanjut (kasus insiden).
  - `exit 1` + CSV hilang atau `OK==0` → `throw` (total failure, disengaja).
  - `exit 2/3/4` (config/model/output) → `throw` selalu walau CSV ada (R1).
  - `Import-Csv` gagal (CSV korup) → `$genOkRows=0` → `throw`; daftar gagal masuk `catch` kuning non-fatal.
  - `Write-FailedList -NoClobber` basi → diatasi via `Remove-Item` sebelum tulis (G6); jangan ubah fungsi helper global.
- **Test:** S3 (sintaks+pytest), S4 (fixture), S5 (recovery).
- **Input & expected:** Insiden nyata: `exit 1`, `genOkRows=96` → tidak `throw`; `m.OK=96`; `failed_05_metadata.txt=1 baris` (`039_...-adu.jpg`); `Add-Stage PARTIAL`; Tahap 6 jalan (96 file per `for_*`).
- **Command verifikasi:** Lihat S3/S4/S5.
- **Hasil diharapkan:** Lihat S4/S5.
- **Completion criteria:** (a) diff hanya baris 1074-1087; (b) `exit 2/3/4` masih `throw`; (c) `exit 1`+96 sukses → `PARTIAL` + lanjut.
- **Tidak boleh diubah di langkah ini:** Tahap 3V, helper `Write-FailedList/Get-MissingBasenames/ConvertTo-EmbedCsvs`, summary, Embed scripts, generator Python, baris di luar 1074-1087.

---

## S2 — Paritas Tahap 3V vektor (Tier-3 generate)

- **Tujuan:** Terapkan toleransi identik S1 pada jalur SVG/EPS agar 1 gagal metadata tidak membunuh trace/preview/eps.
- **Finding:** G2, G3, G4, G5, G6.
- **Dependency:** S1 (wajib meniru pola + nama variabel + teks warning yang sama; jangan desain ulang).
- **File yang harus dibaca:** `Orchestrate-Stock.ps1:1133-1175` (seluruh Tahap 3V termasuk Tier-1 reuse dan Tier-2 rebuild sebagai konteks jangan-diubah).
- **File yang harus diubah:** `Orchestrate-Stock.ps1` HANYA baris 1163-1174 (cabang `else { $runBat...; cmd /c...; throw...; ConvertTo...; Add-Stage...; throw m.OK==0 }`).
- **Simbol terkait:** Sama seperti S1 plus `$haveSmall`, `$genComplete`, `$Force`, Tier-1 `$reuseFull`, Tier-2 `Test-GenCsvComplete`.
- **Kondisi saat ini:**
  ```powershell
  } else {
    $runBat = Join-Path $GenDir "run.bat"
    $genCmd = "`"$runBat`" generate `"$small`" --output-dir `"$rawDir`" --backend $($script:MetadataBackend)"
    Write-Host ("  > {0}" -f $genCmd) -ForegroundColor DarkGray
    cmd /c $genCmd
    if ($LASTEXITCODE -ne 0) { throw "Generate metadata gagal (exit $LASTEXITCODE) - lihat $rawDir\processing.log." }
    if (-not (Test-Path -LiteralPath $genCsv)) { throw "metadata.csv tidak ditemukan di $rawDir." }
  }
  $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $vectCsv $pixCsv $Copyright $Creator $haveSmall
  Write-Host ("  Metadata: ...") -ForegroundColor Green
  Add-Stage 3 "Metadata" "OK" "$($m.OK) OK, $($m.Failed) gagal"
  if ($m.OK -eq 0) { throw "Tidak ada metadata sukses untuk di-embed." }
  ```
- **Perubahan konkret (cermin S1, dengan 2 penyesuaian nama):** ganti isi `else` + 3 baris setelahnya dengan:
  ```powershell
  } else {
    $runBat = Join-Path $GenDir "run.bat"
    $genCmd = "`"$runBat`" generate `"$small`" --output-dir `"$rawDir`" --backend $($script:MetadataBackend)"
    Write-Host ("  > {0}" -f $genCmd) -ForegroundColor DarkGray
    cmd /c $genCmd
    $genExit = $LASTEXITCODE
    $genCsvExists = Test-Path -LiteralPath $genCsv -PathType Leaf
    $genOkRows = 0
    if ($genCsvExists) {
      try { $genOkRows = @(Import-Csv -LiteralPath $genCsv -Encoding UTF8 -ErrorAction Stop | Where-Object { $_.status -in @("success","skipped") }).Count } catch { $genOkRows = 0 }
    }
    if (($genExit -ne 0) -and (($genExit -ne 1) -or (-not $genCsvExists) -or ($genOkRows -eq 0))) { throw "Generate metadata gagal (exit $genExit) - lihat $rawDir\processing.log." }
    if (-not $genCsvExists) { throw "metadata.csv tidak ditemukan di $rawDir." }
    if (($genExit -eq 1) -and ($genOkRows -gt 0)) { Write-Host ("  [!] Generate metadata partial (exit 1): {0} sukses, lanjut dengan file sukses." -f $genOkRows) -ForegroundColor Yellow }
  }
  $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $vectCsv $pixCsv $Copyright $Creator $haveSmall
  Write-Host ("  Metadata: {0} OK, {1} gagal, {2} tanpa file-output (dilewati), Vecteezy={3}, Pixabay={4} -> {5}" -f $m.OK, $m.Failed, $m.FilteredOut, $m.Vecteezy, $m.Pixabay, $metaDir) -ForegroundColor Green
  $failedMeta = Join-Path $stock "failed_03_metadata.txt"
  Remove-Item -LiteralPath $failedMeta -Force -ErrorAction SilentlyContinue
  try {
    $failedNames = @(Import-Csv -LiteralPath $genCsv -Encoding UTF8 -ErrorAction Stop | Where-Object { $_.status -notin @("success","skipped") } | ForEach-Object { "$($_.filename)" } | Where-Object { $_ } | Sort-Object -Unique)
    if ($failedNames.Count -gt 0) { Write-FailedList $failedMeta $failedNames }
  } catch { Write-Host ("  [!] Gagal menghitung daftar metadata gagal: {0}" -f $_.Exception.Message) -ForegroundColor Yellow }
  if ($genExit -eq 1) { Add-Stage 3 "Metadata" "PARTIAL" "$($m.OK) OK, $($m.Failed) gagal (exit 1, lihat failed_03_metadata.txt)" }
  else { Add-Stage 3 "Metadata" "OK" "$($m.OK) OK, $($m.Failed) gagal" }
  if ($m.OK -eq 0) { throw "Tidak ada metadata sukses untuk di-embed." }
  ```
  Nama file memakai `failed_03_metadata.txt` (beda dari `failed_03_upscale.txt` JPG agar tidak tabrakan). Filter memakai `$haveSmall` (metadata vektor dari JPG kecil, bukan `$haveFinal`) — jangan tukar.
- **Urutan dalam file:** Sama seperti S1; Tier-1 (`$reuseFull`) dan Tier-2 (`$genComplete` rebuild) di atasnya TIDAK disentuh.
- **Behavior dipertahankan:** Tier-1 reuse tanpa API, Tier-2 rebuild tanpa API, `ConvertTo-EmbedCsvs ... $haveSmall`, Tahap 4V/5V/6V/7V, stale-cleanup vektor.
- **Error handling/edge:** Identik S1. Tambahan: bila Tier-1 reuse aktif, blok ini tidak dieksekusi (tidak ada `$genExit`) — `Add-Stage SKIP` lama berlaku; jangan referensikan `$genExit` di luar blok `else`.
- **Test:** S3 + S4 varian vektor.
- **Input & expected:** Stub `exit 1` + 2 sukses/1 gagal → `PARTIAL` + lanjut trace; `exit 2` → `throw`.
- **Command verifikasi:** S3/S4.
- **Hasil diharapkan:** S4.
- **Completion criteria:** (a) diff hanya baris 1163-1174; (b) Tier-1/2 tidak berubah; (c) filter tetap `$haveSmall`.
- **Tidak boleh diubah di langkah ini:** Blok S1, Tier-1/2, tahap vektor lain, helper global, Embed, generator.

---

## S3 — Sintaks PowerShell + kontrak pytest generator (tanpa API)

- **Tujuan:** Pastikan edit S1-S2 tidak merusak parse dan tidak mengubah kontrak exit generator.
- **Finding:** G4 (regresi kontrak).
- **Dependency:** S1, S2.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` (hasil edit), `microstock-metadata-generator/tests/test_cli.py:74-85`.
- **File yang harus diubah:** TIDAK ADA (verifikasi saja).
- **Simbol terkait:** `System.Management.Automation.Language.Parser`, `pytest`, `test_partial_batch_failure_exit_code`.
- **Kondisi saat ini:** N/A.
- **Perubahan konkret:** N/A.
- **Urutan:** (1) parse PS; (2) pytest file tunggal.
- **Behavior dipertahankan:** N/A.
- **Error handling/edge:** Bila parse error, perbaiki S1/S2 dulu (lokasi dari pesan parser), jangan edit file lain. Bila pytest gagal, pastikan tidak ada file Python yang diubah (`git status` harus bersih untuk `microstock-metadata-generator/`).
- **Test:** (a) parser; (b) `tests/test_cli.py`.
- **Input & expected:** (a) input file PS hasil edit; (b) suite CLI dengan model mocked (tanpa API key, tanpa model asli).
- **Command verifikasi:**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Side\Microstock\Orchestrate-Stock.ps1', [ref]$null, [ref]$e); if ($e.Count -gt 0) { $e | ForEach-Object { $_.Message } ; exit 1 } else { 'PARSE-OK' }"
  C:\Side\Microstock\microstock-metadata-generator\.venv\Scripts\python.exe -m pytest tests/test_cli.py -q
  ```
  Jalankan pytest dengan workdir `C:\Side\Microstock\microstock-metadata-generator`.
- **Hasil diharapkan:** `PARSE-OK`; pytest `7 passed` (atau minimal `test_partial_batch_failure_exit_code PASSED` + tidak ada failure); `test_partial_batch_failure_exit_code` tetap mengharapkan `code == 1`.
- **Completion criteria:** Kedua command hijau; `git status --porcelain microstock-metadata-generator/` kosong.
- **Tidak boleh diubah:** File Python mana pun; `_stock`; `.env*`.

---

## S4 — Fixture offline deterministik (tanpa API, tanpa model)

- **Tujuan:** Buktikan cabang baru bereaksi benar pada `exit 1` vs `exit 2` tanpa biaya API.
- **Finding:** G1-G5 (end-to-end logika).
- **Dependency:** S1-S3.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1:431-451` (untuk dot-source `ConvertTo-EmbedCsvs`).
- **File yang harus diubah:** TIDAK ADA di repo (fixture hanya di `%TEMP%`, hapus setelah selesai).
- **Simbol terkait:** `ConvertTo-EmbedCsvs`, `Write-FailedList`, `Import-Csv` status filter.
- **Kondisi saat ini:** N/A (lingkungan uji baru).
- **Perubahan konkret:** N/A (uji logika via dot-source; `Orchestrate-Stock.ps1` aman di-dot-source karena ekor file memakai `if ($MyInvocation.InvocationName -ne ".") { Main }` sehingga tidak auto-run).
- **Urutan:** (1) buat fixture TEMP; (2) dot-source; (3) panggil fungsi; (4) asersi; (5) hapus TEMP.
- **Behavior dipertahankan:** N/A.
- **Error handling/edge:** Fixture di `C:\Users\alama\AppData\Local\Temp\opencode\meta-partial-<GUID>\`, bukan di repo. Wajib hapus setelah lulus/gagal.
- **Test yang ditambahkan:** TIDAK ADA file test baru di repo (repo PS tidak punya Pester; jangan buat harness baru di langkah ini — catat sebagai rekomendasi lanjutan).
- **Input test:** Buat `gen.csv` dengan 3 baris: `a.jpg/success`, `b.jpg/success`, `c.jpg/failed` (kolom minimal `filename,status,title,description,keywords,category`). Buat `final/` berisi `a.jpg,b.jpg` (2 file dummy, isi bebas — hanya basename yang dibaca). Panggil:
  ```powershell
  . 'C:\Side\Microstock\Orchestrate-Stock.ps1'
  $m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $vectCsv $pixCsv "alamaby" "alamaby" @("a","b")
  ```
- **Expected result:** `$m.OK -eq 2`, `$m.Failed -eq 1`, `$m.FilteredOut -eq 0`; tiap CSV embed tepat 2 baris; daftar gagal turunan (`Where status -notin success,skipped`) = `@("c.jpg")` 1 baris. Simulasi guard S1: `$genExit=1,$genOkRows=2` → lanjut (tidak throw); `$genExit=2` → throw; `$genExit=1,$genOkRows=0` → throw.
- **Command verifikasi:** Snippet di atas +:
  ```powershell
  Import-Csv $adobeCsv -Encoding UTF8 | Measure-Object | Select-Object -ExpandProperty Count
  ```
  Ekspektasi `2`.
- **Hasil diharapkan:** Semua asersi hijau; CSV 2 baris; guard 3 kasus (1-lanjut, 2-throw, 1+0-throw) sesuai.
- **Completion criteria:** S4 lulus tanpa memanggil API/model; tidak ada file repo berubah (`git status --porcelain` hanya `M Orchestrate-Stock.ps1` dari S1-S2).
- **Tidak boleh diubah:** `_stock` nyata, `microstock-metadata-generator/`, Embed scripts, `plans/` lain.

---

## S5 — Recovery offline data nyata `natal_261006_1543` (tanpa API)

- **Tujuan:** Buktikan 96 sukses yang terbuang dapat dipulihkan tanpa API ulang, memakai `metadata.csv` mentah yang sudah ada.
- **Finding:** G1 (pemulihan nilai 04:07:42 yang hilang).
- **Dependency:** S1-S4 (logika sudah benar; langkah ini hanya pembuktian, bukan edit).
- **File yang harus dibaca:** `natal_261006_1543/generated/_stock/metadata/raw/metadata.csv`, `natal_261006_1543/generated/_stock/04_final_jpg/` (97 file), `Embed-JpgMetadata.ps1` (pahami argumen `CsvPath/JpgDir/OutDir` saja, jangan ubah).
- **File yang harus diubah:** TIDAK ADA file repo. Output pemulihan ditulis ke direktori TEMP (`<temp>\natal-recovery\`), BUKAN ke `_stock\for_*` nyata — agar langkah ini read-only terhadap data produksi dan deterministik untuk model kecil. Pengisian `_stock\for_*` nyata dilakukan operator setelah plan diterima, via rerun normal (lihat Notes).
- **Simbol terkait:** `ConvertTo-EmbedCsvs`, `Embed-JpgMetadata.ps1`, `Repair-VecteezyPackage` (jangan panggil manual — hanya via rerun operator).
- **Kondisi saat ini:** `raw/metadata.csv`=97 baris (96 success + 1 failed `039_...`); `04_final_jpg`=97 file; `metadata/*.csv`=0; `for_*`=0.
- **Perubahan konkret:** TIDAK ADA di repo. Di TEMP:
  1. Dot-source `Orchestrate-Stock.ps1`.
  2. `$haveFinal` dari `04_final_jpg` nyata (read-only).
  3. `ConvertTo-EmbedCsvs` dengan output ke TEMP → harapkan `OK=96, Failed=1`.
  4. Panggil `Embed-JpgMetadata.ps1` 4x (adobe/dreamstime/vecteezy/pixabay CSV TEMP → `JpgDir=04_final_jpg` nyata → `OutDir=TEMP`) → harapkan 96 JPG per folder TEMP.
- **Urutan:** Convert → hitung CSV (96 baris tiap file) → embed 4x → hitung output (96 tiap folder).
- **Behavior dipertahankan:** File sumber nyata tidak ditulis; basename dipertahankan.
- **Error handling/edge:**
  - Jika `OK != 96`, hentikan dan laporkan (data berubah sejak baseline).
  - Jika embed menghasilkan != 96, bedakan: 95 = kemungkinan `039` gagal ikut terfilter dengan benar vs 97 = filter `$haveFinal` bocor — catat sebagai temuan baru.
  - Jangan hapus/copy ke `_stock\for_*` nyata di langkah ini. Rerun nyata (operator, setelah kode fix di-merge): `.\Orchestrate-Stock.ps1 -SourceDir "C:\Side\Microstock\natal_261006_1543\generated" -Target JPG -Scale 5 -Copyright "alamaby" -Creator "alamaby"` tanpa `-Force` (checkpoint resume: 96 skip, 1 retry API). Ekspektasi operator: `for_adobe/for_dreamstime/for_vecteezy_photo/for_pixabay_photo` = 96 tiap folder, `failed_05_metadata.txt` = 1 baris bila retry masih gagal, summary `PARTIAL` kuning bila 1 gagal persist.
- **Test:** N/A (pembuktian manual).
- **Input & expected:** Input nyata di atas; expected TEMP: 4 CSV × 96 baris; 4 folder × 96 JPG.
- **Command verifikasi:**
  ```powershell
  Import-Csv '<temp>\natal-recovery\<batch>_metadata_adobe.csv' -Encoding UTF8 | Measure-Object | Select-Object -ExpandProperty Count
  Get-ChildItem '<temp>\natal-recovery\for_adobe' -File -Filter '*.jpg' | Measure-Object | Select-Object -ExpandProperty Count
  ```
  Ganti `<temp>` dan `<batch>` (`generated` → batch name = `generated`? Catatan: batch = nama folder sumber = `generated`, jadi file = `generated_metadata_adobe.csv` — verifikasi nama aktual via `Get-ChildItem` bila ragu, jangan menebak).
- **Hasil diharapkan:** `96` dan `96`.
- **Completion criteria:** Angka TEMP `96/96` tercapai; repo tetap hanya `M Orchestrate-Stock.ps1`; data nyata tak tersentuh.
- **Tidak boleh diubah:** `_stock\for_*` nyata, `_stock\metadata\*.csv` nyata, `_stock\metadata\raw\*`, `.env*`, generator, Embed scripts.

---

## Open Questions / Blocker

1. **Retry otomatis 1 file gagal (`039`) vs catat-dan-lanjut?** Opsi A (dipakai plan ini): catat `failed_05_metadata.txt` + lanjut 96; retry terjadi alami pada rerun berikutnya via checkpoint (1 file, murah). Opsi B (ditolak untuk plan ini): loop retry inline 3x di orchestrator — ditolak karena generator sudah retry 3x (`attempt_count: 3`) dan retry inline menambah 4 jam bila API timeout massal. Rekomendasi: Opsi A. Risiko Opsi A: bila 1 file gagal karena bug prompt sistemik, rerun akan gagal lagi — mitigasi: `failed_items.json` (`InvalidModelResponseError/Empty`) menandakan transient, bukan bug prompt.
2. **Ubah `Write-FailedList -NoClobber` global ke `-Force`?** Opsi A (dipakai): jangan ubah global; tiap situs baru `Remove-Item` dulu (blast radius minimal). Opsi B: ubah helper global — ditolak karena 6 tahap lama ikut berubah perilaku. Rekomendasi: Opsi A.
3. **Nomor vs nama kategori Adobe (`Category`)?** Tidak diputuskan di plan ini (kode `Get-AdobeCategory` tidak disentuh). Bukan blocker untuk partial-metadata.

---

## Handoff Checklist (untuk model implementer kecil)

- [ ] Kerjakan berurutan S0 → S1 → S2 → S3 → S4 → S5; jangan loncat.
- [ ] Sebelum edit, baca file pada nomor baris persis yang dirujuk (S0 daftar 1-11).
- [ ] Edit HANYA `Orchestrate-Stock.ps1:1074-1087` (S1) dan `:1163-1174` (S2); tempel blok kode persis apa adanya (jangan parafrase, jangan refactor, jangan ubah nama variabel `$genExit/$genOkRows/$failedMeta/$failedNames`).
- [ ] Jangan ubah: `microstock-metadata-generator/**`, `Embed-JpgMetadata.ps1`, `Embed-VectorMetadata.ps1`, child convert/upscale/trace/preview/eps, `Process-Batch.ps1`, `Rename-Numbered.ps1`, helper global selain dipanggil, summary selain dipakai, `_stock/**` nyata, `.env*`, `plans/` lain.
- [ ] S3 wajib hijau (`PARSE-OK` + pytest `test_cli.py`, kontrak `code == 1` tetap).
- [ ] S4 wajib hijau di TEMP (2/1/0 + 3 kasus guard); hapus fixture TEMP setelah selesai.
- [ ] S5 hanya ke TEMP (96/96); JANGAN tulis `_stock\for_*` nyata; JANGAN panggil API; JANGAN stage/commit.
- [ ] Akhir: `git status --porcelain` hanya boleh `M Orchestrate-Stock.ps1` (plus file plan ini `?? plans/2026-10-11-metadata-partial-failure-plan.md`). Bila ada `M` lain, revert dan ulangi.
- [ ] Bila angka S0/S5 tidak cocok (bukan 97/96/1/0) atau guard berperilaku lain, HENTIKAN dan catat temuan baru — jangan perluas scope diam-diam.

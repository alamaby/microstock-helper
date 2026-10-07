# Partial-Failure Tolerance: JPG + Vector Pipeline

Created: 2026-10-07 12:00:00

## Objective

Satu file rusak di satu tahap batch (kasus nyata: `[TAHAP 4] Convert JPG final`, 46/47 sukses di `C:\Side\Microstock\autumn_261005\generated`) tidak boleh menggagalkan seluruh run orchestrator dan tidak boleh melewatkan embed untuk 46 file yang sukses. Setiap tahap batch harus: lanjut dengan file sukses, mencatat daftar gagal ke file recovery, dan dapat dipulihkan via rerun idempoten. Berlaku untuk semua tahap JPG (2, 3, 4) dan vektor (4V, 5V, 6V).

## Scope

- `Convert-PngToJpg.ps1` (kontrak exit-code partial)
- `Convert-WebpToJpg.ps1` (kontrak exit-code partial)
- `Upscale.ps1` (tambah exit-code eksplisit, selama ini selalu 0)
- `Trace-Svg.ps1` (kontrak exit-code partial)
- `Export-VectorPreview.ps1` (kontrak exit-code partial)
- `Convert-SvgToEps.ps1` (kontrak exit-code partial)
- `Orchestrate-Stock.ps1` (toleran partial per tahap + daftar gagal + filter metadata + summary PARTIAL)

## Milestones

1. Kontrak exit-code child script diseragamkan (Langkah 1-2).
2. Orchestrator toleran partial + recovery file (Langkah 3-6).
3. Metadata/embed hanya memproses file yang benar-benar ada (Langkah 7).
4. Ringkasan jujur + verifikasi ujung-ke-ujung (Langkah 8-9).

## Tasks

- [x] Langkah 1: Seragamkan exit-code partial pada 5 child script (convert/trace/preview/eps)
- [x] Langkah 2: Tambah exit-code eksplisit pada Upscale.ps1
- [x] Langkah 3: Tambah helper recovery di Orchestrate-Stock.ps1
- [x] Langkah 4: Terapkan pola partial di TAHAP 2 (convert kecil)
- [x] Langkah 5: Terapkan pola partial di TAHAP 3 (upscale) + TAHAP 4 (JPG final)
- [x] Langkah 6: Terapkan pola partial di TAHAP 4V/5V/6V (trace/preview/eps)
- [x] Langkah 7: Filter metadata terhadap output yang ada
- [x] Langkah 8: Status PARTIAL di summary + petunjuk recovery
- [x] Langkah 9: Verifikasi manual per tahap + rerun recovery

## Risks

- R1: "Lanjut walau ada gagal" menyamarkan kerusakan sistemik (mis. ffmpeg rusak → semua file gagal). Mitigasi: `throw` FATAL tetap dipakai bila output valid `=0`; partial hanya bila `>0` output valid.
- R2: Rerun menimpa output baik bila `-Force` dipakai sembarangan. Mitigasi: recovery default tanpa `-Force` (skip output valid); `-Force` hanya untuk file gagal spesifik.
- R3: Perubahan exit-code mengubah perilaku pemanggil manual di luar orchestrator (user menjalankan `Convert-PngToJpg.ps1` langsung dan mengandalkan `exit 1` sebagai "ada yang gagal"). Mitigasi: banner/summary tetap mencetak `Failed: N` + daftar file; hanya kode exit yang berubah. Dicatat di Langkah 1.

## Progress Log

- 2026-10-07 12:00:00 — Plan dibuat dari analisis log `autumn_261005\generated\_stock\orchestrator.log` + inspeksi kode. Belum ada implementasi.
- 2026-10-07 — Langkah 1+2 selesai: 5 child script memakai kontrak Opsi A (`exit 1` hanya bila nol output valid + `exit 0` eksplisit); `Upscale.ps1` tambah 2 baris exit eksplisit di akhir.
- 2026-10-07 — Langkah 3 selesai: `Write-FailedList` + `Get-MissingBasenames` ditambah setelah `Add-Stage` di `Orchestrate-Stock.ps1` (keduanya tidak throw).
- 2026-10-07 — Langkah 4+5 selesai: TAHAP 2/3/4 memakai pola `$partialN` + `failed_*.txt` + `Add-Stage PARTIAL`; `throw` dipertahankan bila count output 0.
- 2026-10-07 — Langkah 6 selesai: pola sama di TAHAP 4V/5V/6V (`failed_04_trace-svg.txt`, `failed_05_preview-jpg.txt`, `failed_06_svg-eps.txt`).
- 2026-10-07 — Langkah 7 selesai: `ConvertTo-EmbedCsvs` tambah param `$OnlyBasenames` + properti balik `FilteredOut`; TAHAP 5 JPG filter via basename `04_final_jpg`, TAHAP 3V via basename `02_jpg_small`.
- 2026-10-07 — Langkah 8 selesai: summary PARTIAL kuning + blok pemulihan `failed_*.txt`; status akhir `PARTIAL` bila partial tanpa FATAL; `exit 1` akhir hanya bila ada `GAGAL`; `Invoke-Child` dibungkus try/catch (return -1 saat child throw — temuan verifikasi, lihat Notes).
- 2026-10-08 — Tindak lanjut rekomendasi deviasi selesai: (R1) warning partial pindah ke cabang `miss.Count -gt 0` di semua tahap 2/3/4/4V/5V/6V (tahap 2 menyimpan `$codeWebp`/`$codePng` terpisah agar info exit tetap ada); (R2) `Invoke-Child` catch mencetak 5 baris pertama `ScriptStackTrace` (masuk transcript `orchestrator.log`); (R3) loop `Convert-WebpToJpg.ps1` di-hardening — seluruh badan per-file termasuk `Test-HasAlpha` masuk `try` (`Convert-PngToJpg.ps1` diverifikasi sudah hardened, tidak diubah). Verifikasi: fixture webp korup identik kasus P5 kini `exit 0` + 2/3 output (dulu throw→FATAL); rerun `exit 0` (SKIP); syntax OK; fixture TEMP dihapus.

---

## Finding → Langkah Traceability

| Finding | Deskripsi | Ditangani |
|---|---|---|
| F1 | 1 file gagal di TAHAP 4 → `throw "Convert final gagal (exit 1)."` → tahap 5+6 tidak jalan untuk 46 file sukses | Langkah 1 + 5 + 7 + 8 |
| F2 | Pola abort-on-partial yang sama di TAHAP 2, 3, 4V, 5V, 6V | Langkah 1 + 4 + 5 + 6 |
| F3 | Kontrak exit-code inkonsisten: 5 script `exit 1` saat partial; `Upscale.ps1` tidak pernah non-zero; `Embed-JpgMetadata.ps1` tidak pernah non-zero; `Embed-VectorMetadata.ps1:324` `exit 1` saat partial | Langkah 1 + 2 (embed TIDAK diubah, lihat larangan) |
| F4 | Tidak ada artefak recovery (daftar gagal tidak dipersist; resume hanya kebetulan via skip idempoten) | Langkah 3 + 8 + 9 |
| F5 | Metadata/embed berpotensi memproses baris yang file-nya tidak ada di output tahap sebelumnya | Langkah 7 |
| F6 | Summary hanya mengenal OK/SKIP/FATAL; partial dilaporkan sebagai FATAL berhenti | Langkah 8 |

## Keputusan Desain (final, jangan diubah implementer)

**Kontrak exit-code baru (Opsi A, DIPILIH):** child script batch `exit 0` bila `($ok + $skipped) -gt 0`, walau `$failed -gt 0`. `exit 1` hanya bila nol output valid (`($ok + $skipped) -eq 0` dan `$total -gt 0`) atau error fatal environment/argumen (binary hilang, folder sumber tak ada — blok yang sudah `exit 1` hari ini, tidak diubah).
**Opsi B (DITOLAK, dokumentasi saja):** `exit 2` khusus partial. Ditolak karena: (a) semua pemanggil luar + dokumentasi mengasumsikan 0=ok/bukan-0=gagal; (b) `Invoke-Child` + `cmd /c` + `$LASTEXITCODE` perlu cabang baru di tiap tahap; (c) tidak ada consumer yang butuh beda OK-vs-PARTIAL via kode proses — orchestrator menghitung ulang dari isi `OutDir`. Implementer WAJIB memakai Opsi A.

---

## Langkah 1 — Seragamkan exit-code partial (5 script)

- **Tujuan:** 1 file gagal tidak lagi menghasilkan `exit 1` bila ada output valid.
- **Finding:** F1, F2, F3.
- **Dependency:** Tidak ada (bisa paralel dengan Langkah 2).
- **File yang harus dibaca:** `Convert-PngToJpg.ps1` (blok 188-210), `Convert-WebpToJpg.ps1` (blok 218-240), `Trace-Svg.ps1` (blok 170-188), `Export-VectorPreview.ps1` (blok 154-172), `Convert-SvgToEps.ps1` (blok 132-150).
- **File yang harus diubah:** kelima file di atas, HANYA blok summary/`exit` akhir.
- **Simbol terkait:** `$ok/$converted`, `$skipped`, `$failed`, `$failedFiles`, `$total`/`$files.Count`.
- **Kondisi saat ini:** tiap file diakhiri pola `if ($failedFiles.Count -gt 0) { ...; exit 1 }` (tanpa `exit 0` eksplisit bila sukses).
- **Perubahan konkret (terapkan identik di 5 file, urutan dalam file: SETELAH blok summary, GANTI blok `if ($failedFiles...)`):**
  1. Pertahankan seluruh cetakan summary + daftar `File gagal` apa adanya (teks tidak berubah).
  2. Ganti `exit 1` tanpa syarat menjadi:
     ```powershell
     if ($failedFiles.Count -gt 0 -and (($converted + $skipped) -eq 0)) { exit 1 }
     ```
     dengan penyesuaian nama counter per file: `Convert-*.ps1` memakai `$converted`; `Trace-Svg/Export-VectorPreview/Convert-SvgToEps.ps1` memakai `$ok` (ganti `$converted` → `$ok`).
  3. Bila `$failedFiles.Count -eq 0`, tambah `exit 0` eksplisit di akhir (kecuali file yang sudah memilikinya — tidak ada yang punya; jadi tambah di semua).
  4. JANGAN ubah: blok validasi environment/argumen di kepala file (`exit 1` untuk binary hilang/folder tak ada tetap), logika loop konversi, `Test-MediaOk/Test-SvgOk/Test-JpgOk/Test-EpsOk`, tulis atomis `.tmp`.
- **Behavior yang dipertahankan:** output console identik; skip idempoten identik; file output identik.
- **Error handling/edge case:** `$total -eq 0` (tidak ada file sumber) tetap `exit 0` seperti hari ini (blok early-return tidak disentuh). `$failed -eq $total` → `exit 1` (total failure, orchestrator tetap FATAL — disengaja, lihat R1).
- **Test:** fixture manual per script (lihat Langkah 9, kasus P1-P3).
- **Input test & expected:** 3 file valid + 1 file korup (isi acak 100 byte berekstensi sumber) → `exit 0`, output valid = 3, daftar gagal mencetak 1 nama. Semua 4 file korup → `exit 1`.
- **Command verifikasi:** `powershell -NoProfile -ExecutionPolicy Bypass -File .\<Script>.ps1 -SourceDir <fixture> -OutDir <out>` lalu `echo $LASTEXITCODE`; hitung file di `<out>`.
- **Hasil verifikasi yang diharapkan:** exit 0 + 3 file pada kasus partial; exit 1 + 0 file pada kasus total.
- **Completion criteria:** 5 file diubah hanya di blok akhir; `git diff --stat` menunjukkan 5 file; tidak ada perubahan loop/banner.
- **Tidak boleh diubah di langkah ini:** `Orchestrate-Stock.ps1`, `Upscale.ps1`, kedua script Embed, `Process-Batch.ps1`, `Rename-Numbered.ps1`.

## Langkah 2 — Tambah exit-code eksplisit pada Upscale.ps1

- **Tujuan:** samakan `Upscale.ps1` dengan kontrak Opsi A (hari ini selalu `exit 0` implisit bahkan saat semua gagal).
- **Finding:** F3.
- **Dependency:** Tidak ada (paralel dengan Langkah 1).
- **File yang harus dibaca:** `Upscale.ps1` blok 250-267 (summary akhir; tidak ada statement `exit` di file ini).
- **File yang harus diubah:** `Upscale.ps1`, HANYA blok setelah summary (setelah baris `Out-File $LogFile -Append` terakhir).
- **Simbol terkait:** `$ok`, `$skipped`, `$failed`, `$total`.
- **Kondisi saat ini:** tidak ada `exit`; PowerShell mengembalikan 0 selalu.
- **Perubahan konkret (urutan: SETELAH baris summary terakhir, TAMBAH di akhir file, jangan sisip di tengah):**
  ```powershell
  if ((($ok + $skipped) -eq 0) -and ($total -gt 0)) { exit 1 }
  exit 0
  ```
- **Behavior yang dipertahankan:** loop upscale, workaround MAX_PATH via `$TmpIn/$TmpOut`, log `upscayl_*.log`, skip `Test-MediaOk`, teks summary.
- **Error handling/edge case:** validasi awal (`upscayl-bin.exe` hilang, scale di luar 2..5, input=output) tetap `exit 1` seperti hari ini; `$files.Count -eq 0` tetap `exit 0`.
- **Test:** fixture 2 JPG valid (kasus P4: keduanya sukses → `exit 0`); tidak ada fixture "semua gagal upscale" yang murah (upscale 5x lambat) — verifikasi logika via inspeksi + 1 run kecil bila mesin mengizinkan, jika tidak catat sebagai SKIP di handoff.
- **Command verifikasi:** sama seperti Langkah 1 + `echo $LASTEXITCODE`.
- **Hasil yang diharapkan:** `exit 0` bila ≥1 sukses/skip.
- **Completion criteria:** diff hanya penambahan 2 baris di akhir file.
- **Tidak boleh diubah:** logika upscale, model/flag `-z 4 -s`, temp handling.

## Langkah 3 — Tambah helper recovery di Orchestrate-Stock.ps1

- **Tujuan:** sediakan fungsi tunggal untuk (a) menulis daftar file gagal dan (b) memberi status partial — dipakai semua tahap berikutnya.
- **Finding:** F4 (fondasi recovery).
- **Dependency:** Setelah Langkah 1-2 (agar kode exit yang dibaca orchestrator sudah bermakna baru).
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` blok 69-81 (`$script:stages`, `Add-Stage`), blok 133-138 (`Invoke-Child`), blok 483-510 (`catch/finally`/summary/return).
- **File yang harus diubah:** `Orchestrate-Stock.ps1`, HANYA: tambah 2 fungsi baru persis SETELAH fungsi `Add-Stage` (baris 79-81), sebelum `Read-Folder` (baris 83).
- **Simbol terkait:** `Add-Stage`, `$script:stages`, `$stock`.
- **Kondisi saat ini:** tidak ada helper; tiap tahap memakai `if ($code -ne 0) { throw ... }`.
- **Perubahan konkret (urutan dalam file: sisip setelah `Add-Stage`, tidak ubah fungsi lain):**
  1. `function Write-FailedList([string]$ListPath, [string[]]$Items)` — tulis UTF8 tanpa BOM, satu path per baris; buat folder induk bila belum ada; tidak throw bila `$Items` kosong (tulis file kosong + return).
  2. `function Get-MissingBasenames([string]$InDir, [string]$OutDir, [string]$OutFilter, [string]$InFilter)` — bandingkan basename (tanpa ekstensi) file input vs output; return array nama input yang tidak punya pasangan output. Batas: hanya untuk filter sederhana (`*.jpg`, `*.svg`, `*.eps`, `*.png`); pencocokan lintas-ekstensi cukup via basename (contoh: `001_x.png` → `001_x.jpg`).
- **Behavior yang dipertahankan:** `Add-Stage`, `Invoke-Child`, transcript, semua teks banner.
- **Error handling/edge case:** helper tidak boleh `throw` (bungkus IO dengan try/catch → return `@()`/tulis warning); `InDir/OutDir` tidak ada → return `@()`.
- **Test:** tidak ada unit test PS di repo; verifikasi via Langkah 9 (file `failed_*.txt` muncul dan isinya = basename yang gagal).
- **Command verifikasi:** inspeksi `Get-Content <_stock>\failed_*.txt` setelah run fixture partial.
- **Hasil yang diharapkan:** 1 baris = nama file sumber yang gagal.
- **Completion criteria:** 2 fungsi baru ada, tidak ada pemanggil yang diubah di langkah ini.
- **Tidak boleh diubah:** logika tahap mana pun di langkah ini.

## Langkah 4 — Pola partial di TAHAP 2 (convert kecil)

- **Tujuan:** 1 file WEBP/PNG korup tidak menggagalkan TAHAP 2 bila JPG kecil lain tersedia.
- **Finding:** F2.
- **Dependency:** Langkah 1 + 3.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` baris 326-347.
- **File yang harus diubah:** `Orchestrate-Stock.ps1` baris 326-347 saja.
- **Simbol terkait:** `$conv`, `$code`, `$small`, `$nSmall`, `$Force`.
- **Kondisi saat ini:**
  ```powershell
  $code = Invoke-Child ... "Convert-WebpToJpg.ps1" ...; if ($code -ne 0) { throw ... }
  $code = Invoke-Child ... "Convert-PngToJpg.ps1" ...;  if ($code -ne 0) { throw ... }
  ... Add-Stage 2 "Convert kecil" "OK" ...
  if ($nSmall -eq 0) { throw ... }
  ```
- **Perubahan konkret (urutan dalam blok, ganti throw per-script; pertahankan hitung `$nSmall` + throw bila 0):**
  1. Ganti kedua `if ($code -ne 0) { throw ... }` menjadi pengumpul status: `$partial2 = @()`; bila `$code -ne 0`, tambahkan label ("WEBP"/"PNG") ke `$partial2` dan `Write-Host` kuning `"[!] Convert <X> sebagian gagal, lanjut dengan file sukses."` — JANGAN throw.
  2. Setelah `$nSmall` dihitung: bila `$nSmall -eq 0` → `throw` seperti hari ini (total failure). Bila `$nSmall -gt 0` dan `$partial2.Count -gt 0` → `Get-MissingBasenames $SourceDir $small "*.jpg" "*.*"` → `Write-FailedList (Join-Path $stock "failed_02_convert-kecil.txt")` → `Add-Stage 2 "Convert kecil" "PARTIAL" "$nSmall file, gagal: <daftar>"`. Bila tidak ada partial → `Add-Stage ... "OK"` seperti hari ini.
- **Behavior yang dipertahankan:** copy JPG-langsung (baris 334-343), hitung `$nSmall`, throw bila 0.
- **Error handling/edge case:** kedua child `exit != 0` + `$nSmall -gt 0` (mis. dari run sebelumnya) → tetap PARTIAL lanjut, bukan FATAL. `$Force` diteruskan seperti hari ini.
- **Test:** fixture campuran (2 webp valid + 1 webp korup + 1 jpg valid) → TAHAP 2 PARTIAL, `$nSmall` = 3, file `failed_02_convert-kecil.txt` berisi 1 nama.
- **Command verifikasi:** jalankan orchestrator Target JPG pada fixture; baca summary + `failed_02*.txt`; `echo $LASTEXITCODE` di akhir (ekspektasi: 0 bila tahap akhir OK/PARTIAL — lihat Langkah 8 untuk aturan exit akhir).
- **Completion criteria:** run fixture partial melewati TAHAP 2 ke TAHAP 3.
- **Tidak boleh diubah:** TAHAP 0/1, logika rename, tahap lain.

## Langkah 5 — Pola partial di TAHAP 3 (upscale) + TAHAP 4 (JPG final) [BUG UTAMA]

- **Tujuan:** selesaikan bug laporan: 46/47 sukses di TAHAP 4 harus lanjut ke metadata+embed; 1 gagal tercatat + dapat recovery.
- **Finding:** F1 (utama), F2.
- **Dependency:** Langkah 1 + 2 + 3.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` baris 349-378.
- **File yang harus diubah:** `Orchestrate-Stock.ps1` baris 349-378 saja (termasuk blok rename-ekstensi `.jpg`→`.png` baris 356-363 — logika blok itu TIDAK diubah, hanya konteks sekitarnya).
- **Simbol terkait:** `$uargs`, `$up`, `$nUp`, `$fixed`, `$fin`, `$final`, `$nFinal`.
- **Kondisi saat ini:** `if ($code -ne 0) { throw "Upscale gagal..." }`, `if ($code -ne 0) { throw "Convert final gagal..." }`, `Add-Stage ... "OK"`, throw bila count 0.
- **Perubahan konkret (urutan dalam blok):**
  1. TAHAP 3: ganti `throw "Upscale gagal"` dengan pola PARTIAL identik Langkah 4 (kuning lanjut). Setelah hitung `$nUp`: bila 0 → throw hari ini; bila >0 dan `$code -ne 0` → `Get-MissingBasenames $small $up "*.*" "*.jpg"` → `Write-FailedList ... "failed_03_upscale.txt"` → `Add-Stage 3 "Upscale" "PARTIAL"`.
  2. TAHAP 4: ganti `throw "Convert final gagal"` dengan pola sama: bila `$nFinal -gt 0` dan `$code -ne 0` → `Get-MissingBasenames $up $final "*.jpg" "*.*"` → `Write-FailedList ... "failed_04_final-jpg.txt"` → `Add-Stage 4 "JPG final" "PARTIAL" "$nFinal file (+1 gagal, lihat failed_04_final-jpg.txt)"`. Bila `$nFinal -eq 0` → throw hari ini.
  3. JANGAN ubah blok 356-363 (betulkan ekstensi `.jpg`→`.png`).
- **Behavior yang dipertahankan:** parameter `-Force` forwarding, pesan sukses, throw total-failure.
- **Error handling/edge case:** kasus laporan (46/47) → PARTIAL + lanjut TAHAP 5. File gagal TAHAP 4 (`001_..._n.png` di `03_upscaled`) kemungkinan korup: recovery = hapus/perbaiki file itu di `03_upscaled`, rerun orchestrator tanpa `-Force` (46 skip-valid, 1 diproses ulang). Catat di pesan PARTIAL: `"Perbaiki lalu rerun perintah yang sama (tanpa -Force)."`.
- **Test:** reproduksi kasus laporan pada fixture kecil (recall: upscale 5x lambat — gunakan fixture 3 file + 1 PNG korup di `03_upscaled` via run convert-final langsung, LALU run orchestrator penuh pada fixture 3-file untuk jalur lanjut-ke-embed).
- **Input test & expected:** `03_upscaled` berisi 2 PNG valid + 1 PNG korup → TAHAP 4 PARTIAL, `04_final_jpg` = 2 JPG, `failed_04_final-jpg.txt` = 1 baris, TAHAP 5+6 tetap jalan untuk 2 file.
- **Command verifikasi:** orchestrator Target JPG pada fixture; `Get-ChildItem <_stock>\04_final_jpg`; `Get-Content <_stock>\failed_04_final-jpg.txt`; hitung file di `for_adobe`/`for_dreamstime` (=2 per folder).
- **Completion criteria:** partial TAHAP 4 tidak menghentikan run; embed berisi tepat file sukses.
- **Tidak boleh diubah:** TAHAP 5/6 di langkah ini.

## Langkah 6 — Pola partial di TAHAP 4V/5V/6V (trace/preview/eps)

- **Tujuan:** paritas jalur vektor (SVG/EPS) dengan jalur JPG.
- **Finding:** F2.
- **Dependency:** Langkah 1 + 3.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` baris 425-460.
- **File yang harus diubah:** `Orchestrate-Stock.ps1` baris 425-460 saja.
- **Simbol terkait:** `$targs/$svgDir/$nSvg`, `$pargs/$prevDir/$nPrev`, `$eargs/$epsDir/$nEps`.
- **Kondisi saat ini:** tiga `throw` (`"Trace SVG gagal"`, `"Render preview gagal"`, `"Convert EPS gagal"`) + throw bila count 0.
- **Perubahan konkret (terapkan pola PARTIAL yang SAMA PERSIS seperti Langkah 5, tiga kali):**
  1. Trace: gagal-parsial → `Get-MissingBasenames $small $svgDir "*.svg" "*.jpg"` → `failed_04_trace-svg.txt` → `Add-Stage 4 "Trace SVG" "PARTIAL"`.
  2. Preview: → `Get-MissingBasenames $svgDir $prevDir "*.jpg" "*.svg"` → `failed_05_preview-jpg.txt` → `Add-Stage 5 "Preview JPG" "PARTIAL"`.
  3. EPS (hanya jalur EPS): → `Get-MissingBasenames $svgDir $epsDir "*.eps" "*.svg"` → `failed_06_svg-eps.txt` → `Add-Stage 6 "SVG->EPS" "PARTIAL"`.
  4. Throw bila count 0 dipertahankan di ketiganya.
- **Behavior yang dipertahankan:** parameter Width/Force forwarding, pembersihan pasangan basi (baris 466-470, tidak disentuh).
- **Error handling/edge case:** preview/eps memakai output tahap vektor sebelumnya sebagai input (bukan `$small`) — pasangan basename harus konsisten; bila trace partial, preview hanya memproses SVG yang ada (sudah demikian via enumerasi `SvgDir`).
- **Test:** fixture 2 JPG kecil + 1 JPG korup → trace PARTIAL (2 SVG), preview lanjut (2 JPG), `failed_04_trace-svg.txt` = 1 baris.
- **Command verifikasi:** orchestrator Target SVG pada fixture; hitung `05_svg`, `06_preview_jpg`, `failed_*.txt`.
- **Hasil yang diharapkan:** run selesai PARTIAL; paket embed berisi 2 pasangan.
- **Completion criteria:** ketiga tahap memakai pola identik Langkah 4/5.
- **Tidak boleh diubah:** TAHAP 7V embed (sudah toleran), blok stale-cleanup.

## Langkah 7 — Filter metadata terhadap output yang ada

- **Tujuan:** baris metadata untuk file gagal tidak ikut ke embed (hindari SKIP berulang + hitung OK menyesatkan).
- **Finding:** F5.
- **Dependency:** Langkah 4-6 (tahap penentu output sudah partial-aware).
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` fungsi `ConvertTo-EmbedCsvs` (baris 141-180) + blok TAHAP 5 JPG (380-395) + TAHAP 3V (408-423).
- **File yang harus diubah:** `Orchestrate-Stock.ps1`, dua titik saja: (a) TAMBAH parameter opsional pada `ConvertTo-EmbedCsvs`; (b) filter di kedua situs panggil.
- **Simbol terkait:** `ConvertTo-EmbedCsvs($GenCsv, $AdobeCsv, $DreamCsv, $Copyright, $Creator)`, `$r.filename`, `$final`, `$prevDir`.
- **Kondisi saat ini:** semua baris `status success/skipped` dari `metadata.csv` masuk ke CSV embed tanpa cek keberadaan file output.
- **Perubahan konkret (urutan):**
  1. Tambah parameter `[string[]]$OnlyBasenames = @()` pada `ConvertTo-EmbedCsvs`; bila non-kosong, lewati baris yang basenamenya tidak ada di daftar (perbandingan case-insensitive, tanpa ekstensi).
  2. Di TAHAP 5 JPG: sebelum panggil fungsi, bangun `$haveFinal = @(Get-ChildItem -LiteralPath $final -File -Filter "*.jpg" | % { $_.BaseName })`; teruskan sebagai argumen baru. Di TAHAP 3V: `$havePrev = @(Get-ChildItem -LiteralPath $small ...)` — CATATAN: metadata vektor dibangkitkan SEBELUM trace (dari JPG kecil), jadi filter di 3V memakai isi `$small`, bukan `$prevDir`. Di TAHAP 7V tidak ada perubahan (embed vektor sudah skip-per-baris via `pair1/pair2`).
  3. Pesan `Write-Host "Metadata: ..."` ditambah jumlah terfilter: `"Metadata: X OK, Y gagal, Z tanpa file-output (dilewati)"`.
- **Behavior yang dipertahankan:** pemenggalan Title 70/200, cap keyword 49/70, splitting kata Dreamstime + `$Stopwords`, kolom CSV — tidak disentuh.
- **Error handling/edge case:** `$OnlyBasenames` kosong → perilaku lama (tidak filter) — penting untuk kompatibilitas + bila folder output belum ada. `metadata.csv` memakai `filename` JPG-kecil sedangkan `$final` berisi basename sama (asumsi pipeline menjaga basename antar tahap — sudah demikian hari ini).
- **Test:** fixture TAHAP 4 partial (2 JPG final dari 3 sumber) → CSV Adobe/Dreamstime = 2 baris; embed `for_adobe`/`for_dreamstime` = 2 file.
- **Command verifikasi:** `Import-Csv <meta>\*_metadata_adobe.csv | Measure-Object`; bandingkan dengan `Get-ChildItem <_stock>\04_final_jpg`.
- **Completion criteria:** jumlah baris CSV embed == jumlah file output tahap sebelumnya pada run partial.
- **Tidak boleh diubah:** logika keyword/title, generator `run.bat`, script embed.

## Langkah 8 — Status PARTIAL di summary + petunjuk recovery

- **Tujuan:** operator melihat PARTIAL kuning + tahu file apa yang gagal dan perintah recovery-nya (F6, F4-UX).
- **Finding:** F4, F6.
- **Dependency:** Langkah 4-7.
- **File yang harus dibaca:** `Orchestrate-Stock.ps1` baris 483-510 (catch/finally/summary/return) + baris 552-575 (`Main`, rekap antrean, exit akhir).
- **File yang harus diubah:** `Orchestrate-Stock.ps1` blok 483-510 dan 562-575 saja.
- **Simbol terkait:** `$script:stages`, `Add-Stage "!" "BERHENTI" "FATAL"`, `$bad`, `$st`, `$failCount`.
- **Kondisi saat ini:** warna merah untuk semua non-OK/SKIP; `Status=GAGAL` bila ada stage non-OK/SKIP; `exit 1` bila ada dir GAGAL.
- **Perubahan konkret (urutan):**
  1. Loop cetak summary (baris ~492): warna `Yellow` bila `$s.Status -eq "PARTIAL"`, hijau bila OK/SKIP, merah hanya FATAL/GAGAL.
  2. Setelah loop: bila ada stage PARTIAL dan tidak ada FATAL, cetak blok `"  Pemulihan: perbaiki file di failed_*.txt di <stock>, lalu rerun perintah yang sama (tanpa -Force)."` + daftar path `failed_*.txt` yang ada.
  3. Aturan status akhir: `$bad = stages Status -notin ("OK","SKIP","PARTIAL")`; `Status="PARTIAL"` bila ada PARTIAL tanpa FATAL (bukan GAGAL); `exit 1` akhir hanya bila ada `GAGAL`/FATAL. Cetak `[PARTIAL]` di rekap antrean dengan warna kuning.
- **Behavior yang dipertahankan:** format tabel, transcript, path upload/log, antrean multi-direktori.
- **Error handling/edge case:** run dengan PARTIAL + FATAL (mis. tahap akhir 0 output) → tetap GAGAL/FATAL (FATAL menang). Run OK murni → perilaku identik hari ini.
- **Test:** tercakup run fixture Langkah 4-6: summary menampilkan PARTIAL kuning + blok pemulihan; `$LASTEXITCODE` 0 untuk partial-murni.
- **Command verifikasi:** inspeksi visual summary + `echo $LASTEXITCODE`.
- **Completion criteria:** 3 kriteria: (a) PARTIAL kuning, (b) blok pemulihan tercetak, (c) exit 0 untuk partial-murni / exit 1 untuk FATAL.
- **Tidak boleh diubah:** logika `Process-Dir` per tahap, `Main` antrean selain pewarnaan/status.

## Langkah 9 — Verifikasi manual per tahap + rerun recovery

- **Tujuan:** buktikan tiap finding tertutup tanpa test harness baru (repo tidak punya Pester untuk *.ps1).
- **Finding:** semua (F1-F6) — verifikasi akhir.
- **Dependency:** Langkah 1-8 selesai.
- **File yang harus dibaca:** tidak ada file baru; gunakan fixture di `C:\Users\alama\AppData\Local\Temp\opencode\plan-verify\` (buat saat verifikasi, HAPUS setelah selesai — bukan bagian repo).
- **File yang harus diubah:** TIDAK ADA (langkah verifikasi saja).
- **Kasus uji (wajib, urut):**
  - P1 convert partial: fixture 3 PNG valid + 1 PNG korup → `Convert-PngToJpg.ps1` → ekspektasi `exit 0`, 3 JPG, 1 nama di daftar gagal.
  - P2 convert total: 2 PNG korup → ekspektasi `exit 1`, 0 JPG.
  - P3 trace/preview/eps partial: 2 JPG valid + 1 JPG korup → tiap script `exit 0` + output 2 + daftar 1.
  - P4 upscale smoke: 2 JPG kecil valid, `-Scale 2` (CATATAN: jangan 5x agar cepat) → `exit 0`, 2 file. Bila mesin sibuk, boleh SKIP dengan catat alasan (logika hanya 2 baris).
  - P5 orkestrasi JPG partial ujung-ke-ujung: fixture 3 image (1 korup disisip di `03_upscaled` sebelum TAHAP 4 ATAU 1 webp korup di sumber) → ekspektasi: TAHAP 4 PARTIAL, `04_final_jpg`=2, CSV=2 baris, `for_adobe`/`for_dreamstime`=2 file, summary PARTIAL kuning + blok pemulihan, `exit 0`.
  - P6 recovery: hapus/perbaiki 1 file gagal di fixture P5 → rerun perintah SAMA tanpa `-Force` → ekspektasi: tahap terkait OK/PARTIAL-hilang, output menjadi 3, tidak ada duplikasi (idempoten: file sukses di-SKIP).
  - P7 vektor smoke: Target SVG pada fixture 2 valid + 1 korup → trace PARTIAL, preview 2, paket embed 2 pasangan.
- **Command verifikasi (contoh; sesuaikan nama fixture):**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Convert-PngToJpg.ps1 -SourceDir <fix> -OutDir <out>; echo $LASTEXITCODE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Orchestrate-Stock.ps1 -SourceDir <fixdir> -Target JPG -Force
  Get-ChildItem <_stock>\04_final_jpg; Get-Content <_stock>\failed_*.txt
  ```
- **Hasil yang diharapkan:** sesuai tiap kasus di atas; `git status --porcelain` repo hanya menunjukkan 7 file script + (rencana) tanpa file fixture (fixture di TEMP, bukan repo).
- **Completion criteria:** P1-P3 + P5-P6 lulus wajib; P4/P7 boleh SKIP sekali dengan alasan mesin, selain itu wajib lulus.
- **Tidak boleh diubah:** file repo mana pun selama verifikasi kecuali perbaikan bug yang ditemukan (perbaikan masuk sebagai revisi Langkah 1-8, bukan edit diam-diam).

## Notes

- **Open question (sudah diputuskan di plan, bukan blocker):** Opsi B `exit 2` ditolak — lihat "Keputusan Desain". Implementer tidak perlu memilih.
- **Bloker nyata:** (1) Penyebab korupnya `03_upscaled\001_..._n.png` di kasus laporan belum diketahui (log convert tidak menyimpan stderr ffmpeg; file `_stock\02/03/04` di direktori sampel saat ini sudah tidak ada — hanya `for_adobe/for_dreamstime/metadata/orchestrator.log` — sehingga forensik isi file tidak mungkin dari repo). Rekomendasi: saat implementasi tambahkan `-loglevel warning` stderr ke file sementara sudah ada di `$psi` (tidak diubah di plan ini agar scope tetap); investigasi forensik dilakukan terpisah, bukan prasyarat. (2) Upscale 5x lambat (~40 dtk/file) membuat P4/P5 mahal — mitigasi: smoke test `-Scale 2` + catat.
- **Area yang TIDAK BOLEH diubah oleh plan ini (eksplisit):** `Embed-JpgMetadata.ps1`, `Embed-VectorMetadata.ps1` (pemanggil sudah toleran; ubah exit-code-nya di luar scope), `Process-Batch.ps1`, `Rename-Numbered.ps1`, `microstock-metadata-generator/**` (punya suite pytest sendiri — jangan sentuh), `.env*`, `AGENTS.md`, data sampel `autumn_261005/**`, `gemini_chatgptimage_natal/**`, file `_stock/**` mana pun, `plans/**` lain.
- **Contoh kasus laporan untuk referensi:** Total 47, Converted 46, Failed 1 (`03_upscaled\001_836807248_1440752781295769_7251660255302797086_n.png`), `[FATAL] Convert final gagal (exit 1)`, 37:29 menit terbuang karena embed 46 file sukses tidak jalan. Setelah perbaikan, ekspektasi untuk kasus identik: TAHAP 4 PARTIAL, embed 46 file jalan, 1 file tercatat di `_stock\failed_04_final-jpg.txt`.
- **Deviasi terverifikasi dari plan (implementasi, bukan scope creep):**
  - D1 — `Invoke-Child` dibungkus try/catch (return -1 saat child `throw`): temuan P5 — `Convert-WebpToJpg.ps1` me-`throw` pada input korup parah (`$ErrorActionPreference = "Stop"`), sehingga exception lolos sebelum `$LASTEXITCODE` terbaca dan orchestrator FATAL. Tanpa ini kontrak Opsi A tidak berlaku untuk throw. Perilaku luar: warning merah + dihitung partial seperti exit non-zero. SELESAI DITINDAKLANJUTI 2026-10-08: (a) sumber throw dipersempit ke region per-file (seluruh badan loop kini di-`try`, lihat R3 — statement persis tak lagi relevan); (b) catch mencetak 5 baris `ScriptStackTrace` ke transcript; (c) `Convert-PngToJpg.ps1` diverifikasi sudah hardened (`:160-173`), tidak diubah.
  - D2 — Guard `if ($miss.Count -gt 0)` sebelum `Add-Stage PARTIAL` di semua tahap 2/3/4/4V/5V/6V: temuan P6 — rerun tanpa `-Force` memicu guard non-interaktif `Upscale.ps1` (`exit 1` karena output tak kosong) walau nol file hilang; tanpa guard, rerun idempoten salah label PARTIAL. Sekarang PARTIAL hanya bila benar ada basename input tanpa pasangan output. SELESAI DITINDAKLANJUTI 2026-10-08: warning kuning dipindah ke dalam cabang `miss>0` (tahap 2 memakai `$codeWebp`/`$codePng` terpisah agar info exit per-script tetap ada).

## Handoff Checklist (untuk model implementer)

- [ ] Baca file persis pada blok baris yang dirujuk tiap langkah sebelum mengedit.
- [ ] Ikuti "Urutan perubahan di dalam file" — jangan refactor di luar blok yang disebut.
- [ ] Patuhi kontrak Opsi A; jangan perkenalkan `exit 2`.
- [ ] Jangan ubah teks banner/summary selain yang diperintah (kecuali tambahan blok pemulihan Langkah 8).
- [ ] Jalankan P1-P3 + P5-P6 minimal; catat P4/P7 bila SKIP + alasan.
- [ ] `git status --porcelain` akhir hanya berisi 7 file script (kolom M) — tanpa fixture, tanpa `_stock`, tanpa `.env`.
- [ ] Jangan stage/commit apa pun (plan ini hanya dibuat sebagai file; implementasi oleh agen lain).
- [ ] Bila menemukan bug baru selama verifikasi: hentikan, catat sebagai temuan baru, jangan perluas scope diam-diam.

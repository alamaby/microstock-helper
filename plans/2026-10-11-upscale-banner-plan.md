# Upscale Banner: MICROSTOCK → UPSCALE + Audit Typo ASCII Art

Created: 2026-10-11 13:00:00

## Objective

Banner besar tahap upscale (`Upscale.ps1`, fungsi `Show-Banner`) saat ini bertuliskan `MICROSTOCK` (copy-paste dari generator metadata) sehingga sekilas terkecoh dengan tahap metadata. Ganti figlet menjadi `UPSCALE` dengan font dan gaya yang identik, tanpa mengubah logika upscale apa pun. Audit typo ASCII art (`ORCHESTRUTOR` dkk.) sudah dilakukan dan bersih — tidak ada perbaikan typo.

## Scope

- `Upscale.ps1` fungsi `Show-Banner` baris 39-47 saja (5 baris figlet + 1 baris subtitle).
- Verifikasi read-only atas banner lain (tanpa perubahan).

## Milestones

1. Bukti baseline dikunci (S0).
2. Font figlet terkonfirmasi deterministik (S1).
3. Banner diganti + subtitle disesuaikan (S2).
4. Verifikasi sintaks, tampilan, dan scope diff (S3).

## Tasks

- [x] S0 — Baseline audit read-only
- [x] S1 — Konfirmasi font figlet via pyfiglet sekali pakai
- [x] S2 — Ganti figlet MICROSTOCK → UPSCALE + subtitle
- [x] S3 — Verifikasi parser, live-run banner, dan scope diff

## Risks

- R1: Font salah tebak → art baru gayanya beda dari banner lain. Mitigasi: S1 mewajibkan byte-compare render `MICROSTOCK` vs art lama; bila tidak identik, STOP (jangan tebak font lain).
- R2: Karakter art merusak string PowerShell (quote/`$`). Mitigasi: S2 memakai gaya double-quote seperti baris lama + asersi tidak ada `"` dan `$` di art (font standard untuk huruf UPSCALE tidak mengandung keduanya).
- R3: `pip install` mengotori repo/venv proyek. Mitigasi: venv sekali pakai hanya di `%TEMP%`, dihapus di S3.

## Progress Log

- 2026-10-11 13:00:00 — Plan dibuat dari audit read-only: typo scan 15 varian nol hasil; lebar baris tiap banner konsisten; figlet `Upscale.ps1:41-45` identik dengan `console_art.py:13-17` (bukti copy-paste). Belum ada implementasi.
- 2026-10-11 12:15:00 — Implementasi selesai penuh (S0 hingga S3). Font figlet `standard` terkonfirmasi identik dengan `console_art.py:13-17` via pyfiglet di TEMP; banner `Upscale.ps1:41-46` diganti menjadi `UPSCALE` dan subtitle disederhanakan; parser valid `PARSE-OK`; live-run exit 0 dengan banner tercetak rapi; lebar baris figlet konsisten (83,84,82,83,84); diff tepat 6 insertions / 6 deletions hanya pada `Upscale.ps1`; direktori TEMP dibersihkan.

## Notes

- Sisi Python (`console_art.py` BANNER/BANNER_API) sudah benar (itu memang tool metadata) — tidak disentuh.
- `Embed-JpgMetadata.ps1:45-49` memakai figlet MICROSTOCK yang sama, tapi subtitle-nya jelas (`EMBED v2.0 ...`) sehingga tidak membingungkan — temuan luar scope (F3), tidak dikerjakan plan ini.
- `Export-VectorPreview.ps1:34`, `Convert-SvgToEps.ps1:31` memakai banner teks biasa yang sudah menyebut nama tahap — tidak disentuh.

---

## Finding → Langkah Traceability

| Finding | Deskripsi | Scope | Ditangani | Verifikasi |
|---|---|---|---|---|
| F1 | Banner besar `Upscale.ps1:41-45` bertuliskan MICROSTOCK, bukan nama tahapnya | Dalam | S2 | S3 |
| F2 | Dugaan typo `ORCHESTRUTOR` dan typo art lain | Dalam | S0 (hasil: bersih, tanpa perubahan kode) | S0 |
| F3 | `Embed-JpgMetadata.ps1:45-49` pola copy-paste sama | Luar | Tidak dikerjakan | — |

---

## S0 — Baseline audit read-only (tanpa perubahan kode)

- **Tujuan:** Kunci bukti bahwa satu-satunya yang rusak adalah kata pada banner Upscale; art lain sehat.
- **Finding/requirement:** F2 (penuh), fondasi F1.
- **Dependency:** Tidak ada.
- **File yang harus dibaca:**
  1. `Upscale.ps1:39-47` (fungsi `Show-Banner`: 5 baris figlet + subtitle + baris kosong).
  2. `Upscale.ps1:130` (situs panggil `Show-Banner $Scale` — konteks, jangan diubah).
  3. `microstock-metadata-generator/src/microstock_metadata/console_art.py:11-19` (BANNER pembanding).
  4. `Orchestrate-Stock.ps1:863-869` (logo `$logo`, pembanding kerapian).
  5. `Orchestrate-Stock.ps1:1352` (teks `ORCHESTRATOR SUMMARY`).
  6. `Convert-PngToJpg.ps1:38-46`, `Convert-WebpToJpg.ps1:48-55`, `Trace-Svg.ps1:39-46` (pembanding).
- **File yang harus diubah:** TIDAK ADA.
- **Simbol terkait:** `Show-Banner($ScaleLabel)`, `$Scale`, `BANNER`.
- **Kondisi saat ini:** `Upscale.ps1:41-45` = figlet `MICROSTOCK` (indent 2 spasi, gaya double-quote); `:46` = `Write-Host ("              U P S C A L E R   {0} X  (Upscayl CLI)" -f $ScaleLabel) -ForegroundColor Yellow`.
- **Perubahan konkret:** TIDAK ADA. Hanya catat: (a) typo scan 15 varian (`ORCHESTRUTOR|ORCHESTATOR|MICROSTOK[^C]|UPSCAl|UPSCAEL|SUMARY|SUMMERY|CONVTERT|PREVEIW|METADTA|DREMSTIME|ADBOE` + 3 lain setara) = nol hasil; (b) lebar baris: orkestrator 81,81,81,81,80; upscale 94,94,95,95,94; png 82×5; webp 92×5; trace 82,81,82,82,82; (c) art `:41-45` identik dengan `console_art.py:13-17` modulo indent.
- **Urutan:** Baca 1-6, jalankan 2 command verifikasi di bawah, catat angka.
- **Behavior dipertahankan:** N/A.
- **Error handling/edge:** Bila typo scan menemukan hasil atau lebar baris menyimpang >2 char dalam satu banner, hentikan dan catat temuan baru — jangan lanjut ke S1.
- **Test:** N/A (inspeksi).
- **Input & expected:** N/A.
- **Command verifikasi (read-only):**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Select-String -Path 'C:\Side\Microstock\*.ps1' -Pattern 'ORCHESTRUTOR|MICROSTOK[^C]|SUMARY|DREMSTIME' | Select-Object -First 5; 'SCAN-DONE'"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "`$s=@(@('Orchestrate-Stock.ps1',864,868),@('Upscale.ps1',41,45)); foreach (`$x in `$s) { `$l=Get-Content -LiteralPath (Join-Path 'C:\Side\Microstock' `$x[0]) | Select-Object -Skip (`$x[1]-1) -First (`$x[2]-`$x[1]+1); '{0}: {1}' -f `$x[0],(($l | ForEach-Object { `$_.Length }) -join ',') }"
  ```
- **Hasil diharapkan:** `SCAN-DONE` tanpa baris temuan; lebar `81,81,81,81,80` dan `94,94,95,95,94`.
- **Completion criteria:** Kedua command sesuai harapan; angka dicatat di handoff.
- **Tidak boleh diubah:** File repo mana pun; `_stock`; `.env*`; venv proyek.

---

## S1 — Konfirmasi font figlet via pyfiglet sekali pakai (di TEMP)

- **Tujuan:** Buktikan font art lama agar art baru gayanya identik — tanpa menebak.
- **Finding:** F1 (fondasi teknis S2).
- **Dependency:** S0.
- **File yang harus dibaca:** `Upscale.ps1:41-45` (target pembanding).
- **File yang harus diubah:** TIDAK ADA di repo (venv + file kerja hanya di `%TEMP%`).
- **Simbol terkait:** `pyfiglet.figlet_format`, font `standard`.
- **Kondisi saat ini:** Font diduga `standard` (figlet klasik 5-baris untuk kapital tanpa descender) — belum terbukti.
- **Perubahan konkret:** TIDAK ADA di repo. Di `C:\Users\alama\AppData\Local\Temp\opencode\figlet-tmp\` (buat baru, hapus di S3):
  1. `python -m venv .venv` (pakai `python`/`py` yang tersedia; bila tidak ada python, STOP dan catat blocker — jangan install Python).
  2. `.venv\Scripts\python.exe -m pip install pyfiglet`.
  3. Render: `.venv\Scripts\python.exe -c "import pyfiglet; print(pyfiglet.figlet_format('MICROSTOCK', font='standard'))"`.
  4. Bandingkan 5 baris hasil (tanpa trailing newline) dengan isi `Upscale.ps1:41-45` setelah kupas prefix `Write-Host "` + indent 2-spasi dan suffix `" -ForegroundColor Cyan` + rstrip tiap baris. Perbandingan case-sensitive, spasi tengah signifikan, trailing space diabaikan.
- **Urutan:** 1 → 2 → 3 → 4. Bila langkah 4 identik → font terkonfirmasi → catat `font=standard`, lanjut S2. Bila tidak identik → STOP total, catat output aktual sebagai blocker (jangan coba font lain diam-diam).
- **Behavior dipertahankan:** N/A.
- **Error handling/edge:** `pip install` gagal (offline) → STOP + blocker (alternatif: minta operator menyediakan render figlet standard dari mesin lain — di luar plan ini). Huruf kecil/judul tidak dipakai — selalu kapital.
- **Test:** N/A (prosedur kalibrasi).
- **Input & expected:** Input kata `MICROSTOCK`; expected 5 baris identik dengan art lama.
- **Command verifikasi:** Perbandingan manual/diff di langkah 4 (tampilkan kedua versi berdampingan di handoff bila ragu).
- **Hasil diharapkan:** Identik → `font=standard` terkunci untuk S2.
- **Completion criteria:** Ada pernyataan tertulis `font=standard TERKONFIRMASI` + tidak ada file repo berubah (`git status --porcelain --untracked-files=no` kosong).
- **Tidak boleh diubah:** `Upscale.ps1`; venv proyek `microstock-metadata-generator/.venv/`; file repo lain. `pip install` HANYA di venv TEMP.

---

## S2 — Ganti figlet MICROSTOCK → UPSCALE + subtitle

- **Tujuan:** Banner besar tahap upscale menyebut nama tahapnya sendiri.
- **Finding:** F1.
- **Dependency:** S1 (syarat: `font=standard TERKONFIRMASI`; tanpa itu DILARANG mengerjakan S2).
- **File yang harus dibaca:** `Upscale.ps1:39-47` (sebelum edit; baca ulang persis sebelum menempel).
- **File yang harus diubah:** `Upscale.ps1` HANYA baris 41-46 (5 figlet + 1 subtitle). Baris 39-40 (`function Show-Banner($ScaleLabel) {` + `Write-Host ""`) dan 47 (`Write-Host ""`) dan 130 (pemanggil) TIDAK disentuh.
- **Simbol terkait:** `Show-Banner($ScaleLabel)`, `$ScaleLabel`, `-ForegroundColor Cyan/Yellow`.
- **Kondisi saat ini:** Lihat S0 butir Kondisi. Gaya string: double-quote (`Write-Host "  ..."`).
- **Perubahan konkret (urutan dalam file):**
  1. Generate: `.venv\Scripts\python.exe -c "import pyfiglet; print(pyfiglet.figlet_format('UPSCALE', font='standard'))"` di venv TEMP S1 (kata sesuai OQ1 — default `UPSCALE`; varian di tabel bawah).
  2. Verifikasi art: tepat 5 baris non-kosong; tiap baris TIDAK mengandung `"` dan `$` (bila mengandung → STOP, jangan escape diam-diam); lebar baris konsisten (selisih ≤2).
  3. Tempel sebagai baris 41-45 baru: tiap baris = `  Write-Host "` + 2 spasi + isi baris art (rstrip) + `" -ForegroundColor Cyan`. Pertahankan gaya double-quote baris lama (jangan pindah ke single-quote — art mengandung `'` pada glif tertentu dan double-quote sudah terbukti valid oleh parser).
  4. Subtitle baris 46 sesuai OQ2 — default opsi (b) rekomendasi: `  Write-Host ("              UPSCALE {0}X image upscaler (Upscayl CLI)" -f $ScaleLabel) -ForegroundColor Yellow`. Varian di tabel bawah. Interpolasi `-f $ScaleLabel` dan warna Yellow WAJIB dipertahankan.
  5. Jangan ubah indentasi, warna, baris kosong sekitar, atau fungsi lain.
- **Tabel varian (pilih sesuai jawaban OQ1/OQ2; default yang bertanda ★ bila pengguna tidak menjawab):**
  - Kata banner: ★ `UPSCALE` (7 glif, proporsional) | `UPSCALER` (8 glif, cocok dengan subtitle lama).
  - Subtitle: ★ (b) `              UPSCALE {0}X image upscaler (Upscayl CLI)` | (a) biarkan baris 46 lama apa adanya.
- **Behavior dipertahankan:** Signature `Show-Banner($ScaleLabel)`, pemanggilan `:130`, teks info `Model/Input/Output/File/Log`, seluruh logika upscale, exit-code, spinner, summary. Perubahan ini murni kosmetik console.
- **Error handling/edge:** Art kosong / bukan 5 baris / mengandung `"`/`$` → STOP + blocker. Lebar art >100 char → STOP (kemungkinan font salah) + blocker.
- **Test:** S3 (tanpa file test baru — repo tidak punya harness Pester; banner adalah output console, verifikasi via live-run S3).
- **Input & expected:** Input kata OQ1 dengan font S1; expected 5 baris valid + subtitle terinterpolasi skala.
- **Command verifikasi:** Lihat S3.
- **Hasil diharapkan:** Lihat S3.
- **Completion criteria:** (a) diff hanya baris 41-46 `Upscale.ps1`; (b) S3 hijau.
- **Tidak boleh diubah di langkah ini:** Baris di luar 41-46; `Orchestrate-Stock.ps1`; script convert/trace/embed; `console_art.py`; venv proyek; `_stock`; `.env*`.

---

## S3 — Verifikasi parser, live-run banner, dan scope diff

- **Tujuan:** Buktikan file valid, banner tampil benar, dan tidak ada perubahan liar.
- **Finding:** F1 (verifikasi akhir).
- **Dependency:** S2.
- **File yang harus dibaca:** `Upscale.ps1` (hasil edit).
- **File yang harus diubah:** TIDAK ADA (verifikasi + bersih-bersih TEMP saja).
- **Simbol terkait:** `System.Management.Automation.Language.Parser`, `Upscale.ps1 -SourceDir -OutDir`.
- **Kondisi saat ini:** N/A.
- **Perubahan konkret:** N/A, kecuali hapus `C:\Users\alama\AppData\Local\Temp\opencode\figlet-tmp\` setelah hijau.
- **Urutan:** (1) parser; (2) live-run folder kosong; (3) cek lebar baris; (4) scope diff; (5) hapus TEMP.
- **Behavior dipertahankan:** N/A.
- **Error handling/edge:** Parser error → perbaiki S2 (lokasi dari pesan parser). Live-run memicu prompt interaktif (`Read-Folder`) berarti argumen direktori salah — ulangi dengan dua direktori kosong berbeda yang sudah ada (jangan jawab prompt manual). Live-runexit BUKAN 0 → selidiki sebelum lanjut (ekspektasi `exit 0` + teks `Tidak ada image`).
- **Test:** Tidak ada file test baru (kesepakatan plan ini).
- **Input test:** Dua direktori kosong berbeda di TEMP, misalnya `<tmp>\in0\` dan `<tmp>\out0\` (buat dengan `New-Item -ItemType Directory`).
- **Command verifikasi:**
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -Command "`$e=`$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Side\Microstock\Upscale.ps1', [ref]`$null, [ref]`$e); if (`$e.Count -gt 0) { `$e | ForEach-Object { `$_.Message }; exit 1 } else { 'PARSE-OK' }"
  powershell -NoProfile -ExecutionPolicy Bypass -File C:\Side\Microstock\Upscale.ps1 -SourceDir <tmp>\in0 -OutDir <tmp>\out0; echo "EXIT=$LASTEXITCODE"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "`$l=Get-Content -LiteralPath 'C:\Side\Microstock\Upscale.ps1' | Select-Object -Skip 40 -First 5; ($l | ForEach-Object { `$_.Length }) -join ','"
  git diff --stat -- Upscale.ps1; git status --porcelain --untracked-files=no
  ```
- **Hasil diharapkan:** `PARSE-OK`; banner baru tercetak + `Tidak ada image` + `EXIT=0`; 5 lebar konsisten (selisih ≤2); diff tepat `1 file changed, 6 insertions(+), 6 deletions(-)` (5 figlet + 1 subtitle; bila subtitle opsi (a) maka 5/5); `git status` hanya `M Upscale.ps1`.
- **Completion criteria:** Semua hasil sesuai; TEMP `figlet-tmp` + `in0/out0` dihapus; tidak ada file repo lain berubah.
- **Tidak boleh diubah:** File repo mana pun selama verifikasi kecuali perbaikan S2 yang ditemukan (sebagai revisi S2, bukan edit diam-diam).

---

## Open Questions / Blocker

1. **OQ1 — Kata banner: `UPSCALE` vs `UPSCALER`.** Opsi `UPSCALE` (rekomendasi ★): sesuai permintaan pengguna kata-per-kata, 7 glif lebih ramping. Opsi `UPSCALER`: selaras subtitle lama. Risiko `UPSCALER`: redundan dengan subtitle bila subtitle ikut disederhanakan. Rekomendasi: `UPSCALE`. Aturan eksekusi: bila pengguna tidak menjawab, pakai ★ (terdokumentasi di S2, bukan pilihan diam-diam).
2. **OQ2 — Subtitle `:46`: biarkan (a) vs sederhanakan (b).** Opsi (a): blast radius minimal (diff 5 baris). Opsi (b) (rekomendasi ★): `UPSCALE {0}X image upscaler (Upscayl CLI)` — hilangkan redundansi `U P S C A L E R` karena banner sudah menyebutnya, info skala + nama tool tetap ada. Risiko (b): teks subtitle berubah (kosmetik, terlihat di log). Rekomendasi: (b). Aturan eksekusi sama seperti OQ1.
3. **F3 `Embed-JpgMetadata.ps1:45-49`:** pola copy-paste sama, subtitle sudah jelas (`EMBED v2.0 ...`). Opsi: biarkan (rekomendasi ★, plan ini tidak menyentuh) vs susulan ganti figlet → `EMBED`. Bukan blocker; bila pengguna mau, buat plan susulan terpisah.

---

## Handoff Checklist (untuk model implementer kecil)

- [ ] Kerjakan berurutan S0 → S1 → S2 → S3; S2 DILARANG tanpa `font=standard TERKONFIRMASI` dari S1.
- [ ] Jawaban OQ1/OQ2: bila pengguna sudah menjawab, pakai tabel varian S2; bila belum, pakai default ★ persis seperti tertulis.
- [ ] Edit HANYA `Upscale.ps1:41-46`; baca ulang baris itu sebelum menempel; pertahankan double-quote, indent 2-spasi, `-f $ScaleLabel`, warna Cyan/Yellow.
- [ ] Jangan ubah: baris lain `Upscale.ps1`, script lain, `console_art.py`, venv proyek, `_stock/**`, `.env*`, `plans/` lain.
- [ ] S3 wajib hijau semua (parser, live-run `EXIT=0`, lebar konsisten, diff hanya `Upscale.ps1`).
- [ ] Hapus direktori TEMP (`figlet-tmp`, `in0`, `out0`) setelah selesai.
- [ ] Jangan stage/commit apa pun (file plan ini adalah satu-satunya artefak; `git status` akhir hanya `M Upscale.ps1` + `?? plans/2026-10-11-upscale-banner-plan.md`).
- [ ] Bila S1 tidak identik / art mengandung `"`/`$` / live-run tidak `EXIT=0`: HENTIKAN, catat blocker, jangan perluas scope diam-diam.

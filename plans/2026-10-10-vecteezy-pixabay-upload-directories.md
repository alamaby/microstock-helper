# Vecteezy + Pixabay Upload Directories (JPG/SVG/EPS) — Implementation Plan

Created: 2026-10-10 00:00:00

## Objective

Menambah direktori siap-upload Vecteezy dan Pixabay ke `Orchestrate-Stock.ps1` untuk
scope `JPG + SVG + EPS`, tanpa mengubah perilaku Adobe/Dreamstime yang ada:
foto JPG (Vecteezy photo + Pixabay photo), vektor EPS (Vecteezy vector) dan
vektor SVG (Pixabay vector), CSV Vecteezy berkolom `License=free` (keputusan
terkunci), CSV pendamping Pixabay untuk copy-paste tag manual (Pixabay tidak
punya upload CSV), sanitasi nama file Vecteezy (tanpa spasi), dan laporan
validasi warn-only. Seluruh tahap baru harus resume-aware/idempoten dan
toleran-partial seperti kontrak Opsi A yang ada.

Keputusan yang sudah final (jangan dibuka ulang saat implementasi):
- D1: scope `JPG, SVG, EPS` — dikonfirmasi user.
- D2: kolom `License` CSV Vecteezy selalu `free` — dikonfirmasi user
  ("ya free saja"). Tanpa param baru, tanpa nilai `pro`/`editorial`/kosong.
- D3: lisensi Pixabay (irrevocable/perpetual/royalty-free + AI-checkbox manual)
  diterima user ("ya").
- D4: implementasi hanya di PowerShell `Orchestrate-Stock.ps1` (jalur image
  yang benar-benar dipanggil). `microstock-metadata-generator/**` TIDAK
  disentuh — divergensi konstanta Python didokumentasikan sebagai OQ-2, bukan
  diperbaiki diam-diam di plan ini.
- D5: cap keyword Vecteezy = 30 frasa (checklist kontributor resmi, paling
  ketat), Pixabay = 25 kata tunggal (konsisten dengan `PIXABAY_MAX_TAGS=25`
  jalur video). Judul Vecteezy = 70 (reuse Adobe ideal), Pixabay = 100
  (konsisten jalur video). Lihat OQ-1.
- D6: validasi bersifat warn-only (tidak pernah throw/block packaging) —
  mempertahankan kontrak partial-tolerance.
- D7: 4 direktori kind-pure mengikuti konvensi Adobe yang ada:
  `for_vecteezy_photo`, `for_pixabay_photo`, `for_vecteezy_eps`,
  `for_pixabay_svg`. (Bukan `for_vecteezy_vector` generik — alasan di Notes.)

## Scope

In scope (satu file):
- `Orchestrate-Stock.ps1` saja: fungsi `ConvertTo-EmbedCsvs`, 2 fungsi helper
  baru, situs panggil TAHAP 5 + 3V + reuse-tier, pembuatan direktori, TAHAP 6
  (JPG), TAHAP 7V (vektor), sanitasi Vecteezy, validasi warn-only, summary +
  return object.

Out of scope (dilarang diubah, lihat juga daftar global di S1–S8):
- Kedua script Embed, semua child script convert/trace/preview/eps/upscale,
  `Rename-Numbered.ps1`, `Process-Batch.ps1`, `microstock-metadata-generator/**`,
  `.env*`, `AGENTS.md`, data `_stock/**`, `plans/**` lain, `.memory/**`.

## Requirement / Finding Traceability

| ID | Finding / Requirement | Sumber | Ditangani langkah |
|----|----------------------|--------|-------------------|
| F1 | Vecteezy foto: JPG/JPEG sRGB, 4–50MP, 1–50MB, kompresi terendah | riset help-center Vecteezy | S3 (paket), S6 (validasi V1–V4) |
| F2 | Vecteezy vektor: EPS kompatibel Illustrator 10, 4–25MP, 1–50MB, RGB/CMYK, vektor murni (tanpa bitmap linked, tanpa embedded font, outline, layer unlock English) | riset help-center Vecteezy | S4 (paket), S6 (V5), blocker B1 |
| F3 | Vecteezy metadata: Title unik, keywords 10–30 (maks 30), CSV `Filename,Title,Description,Keywords[,License]`, Filename tanpa spasi/tanpa ekstensi untuk FTP, English | riset CSV-upload Vecteezy | S1, S2, S5, S6 (V6) |
| F4 | License terkunci `free` (flat $5/1000 foto-vektor; non-exclusive sehingga paralel dengan Adobe/Dreamstime/Pixabay) | keputusan user + riset PPD Free vs Pro | S1, S2 |
| F5 | Pixabay: lisensi diterima; konten AI wajib centang `AI-generated` manual; JANGAN ubah/strip EXIF (aturan AI disclosure) | keputusan user + ToS/AI-guidelines Pixabay | S3, S4 (tanpa strip EXIF — alasan eksplisit), S8 checklist manual |
| F6 | Pixabay AI: harus pegang full rights; tanpa orang nyata/tiru gaya artist/merek-logo; kurasi (hindari batch near-identical); tajam; tanpa watermark/logo/text-overlay | AI Quality Guidelines Pixabay | S6 (V6–V7, yang bisa diotomatisasi) + checklist manual S8 |
| F7 | Pixabay quality pillars + review menit–jam s/d 2–3 hari; tidak ada angka MP publik | riset Pixabay | S6 (pakai ambang JPG yang sama), Notes |
| F8 | 4 direktori kind-pure (D7) | keputusan desain plan ini | S3, S4, S7 |
| F9 | Resume/idempoten/partial-tolerance (kontrak Opsi A) harus dipertahankan di semua tahap baru | `Upscale.ps1:187-192`, `Orchestrate-Stock.ps1:737-748`, plan 2026-10-07 | Semua langkah (ditegaskan per langkah) |
| F10 | Divergensi: `csv_embed.py:22-23` (`VECTEEZY_MAX_TAGS=50`, `PIXABAY_MAX_TAGS=25`) + `convert_video_rows` (punya vecteezy/pixabay, tanpa License) vs `ConvertTo-EmbedCsvs` PS (hanya adobe/dream) | `csv_embed.py:1-220` vs `Orchestrate-Stock.ps1:318-376` | S1 (keputusan PS-only) + OQ-1/OQ-2 |

## Milestones

1. M1 — Fondasi CSV (S1, S2). Tanpa direktori baru; Adobe/Dream byte-identik.
2. M2 — Packaging 4 direktori (S3, S4). JPG dulu (risiko rendah), lalu vektor.
3. M3 — Keamanan upload (S5 sanitasi, S6 validasi warn-only).
4. M4 — Pelaporan + verifikasi ujung-ke-ujung (S7, S8).

## Tasks

- [x] S1 — `ConvertTo-EmbedCsvs` emit CSV Vecteezy (`License=free`) + Pixabay
- [x] S2 — Wire call-site TAHAP 5 + 3V + reuse-tier untuk 2 CSV baru
- [x] S3 — Direktori + packaging foto JPG (Vecteezy photo + Pixabay photo)
- [x] S4 — Packaging vektor (Vecteezy EPS + Pixabay SVG, guard per-Target)
- [x] S5 — Sanitasi nama file Vecteezy + rewrite CSV paket
- [x] S6 — Laporan validasi warn-only `validation_vecteezy_pixabay.txt`
- [x] S7 — Summary + return object (path upload baru)
- [x] S8 — Verifikasi fixture ujung-ke-ujung E1–E8 (tanpa ubah repo)

---

## Langkah Implementasi

### S1 — `ConvertTo-EmbedCsvs` emit CSV Vecteezy (`License=free`) + Pixabay

- Tujuan langkah: satu-satunya fungsi transform image-pipeline menghasilkan
  4 CSV (adobe/dream/vecteezy/pixabay) dari `$rows` yang sama, dengan
  Adobe/Dream byte-identik seperti hari ini.
- Finding/requirement: F3, F4, F10 (keputusan D4/D5: PS-only, cap 30/25).
- Dependency: tidak ada (langkah pertama; S2–S8 bergantung padanya).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:318-376` (seluruh fungsi `ConvertTo-EmbedCsvs`).
  - `Orchestrate-Stock.ps1:64-72` (`$Stopwords`, dipakai Dreamstime-words).
  - `Orchestrate-Stock.ps1:298-305` (`Get-AdobeCategory`, dipakai baris Adobe).
  - `microstock-metadata-generator/src/microstock_metadata/csv_embed.py:21-28,80-105,128-190`
    (baca saja untuk memahami divergensi F10; JANGAN ubah file ini).
- File yang harus diubah:
  - `Orchestrate-Stock.ps1` lines 318–376 saja.
- Class, function, method, type, atau simbol yang terkait:
  `ConvertTo-EmbedCsvs`, `$GenCsv/$AdobeCsv/$DreamCsv/$Copyright/$Creator/$OnlyBasenames`,
  `$phrases`, `$words`, `$title70`, `$title200`, `$adobe/$dream`,
  `$cols/$adobeCols`, `Export-Csv`, return `@{OK,Failed,FilteredOut}`.
- Kondisi implementasi saat ini:
  Signature `($GenCsv, $AdobeCsv, $DreamCsv, $Copyright, $Creator, [string[]]$OnlyBasenames = @())`;
  loop membangun `$adobe` (frasa cap 49, title 70) dan `$dream` (kata tunggal
  stopword-drop cap 70, title 200); export 2 CSV; return 3 properti.
- Perubahan konkret yang harus dilakukan (urutan dalam fungsi, jangan
  sisip di luar urutan ini):
  1. Baris 318: ganti signature menjadi
     `function ConvertTo-EmbedCsvs($GenCsv, $AdobeCsv, $DreamCsv, $VecteezyCsv, $PixabayCsv, $Copyright, $Creator, [string[]]$OnlyBasenames = @())`.
     Positional — call-site diperbarui di S2, bukan di sini.
  2. Setelah blok `$dream += ...` (baris 362–369, sebelum baris 370 `}` penutup
     foreach): tambah konstruksi dua row baru dari variabel yang SUDAH ada
     (`$phrases`, `$words`, `$r`, `$Copyright`, `$Creator`) — dilarang
     menghitung ulang phrases/words dari `$r.keywords`:
     ```powershell
     $vPhrases = @($phrases); if ($vPhrases.Count -gt 30) { $vPhrases = $vPhrases[0..29] }
     $pWords = @($words); if ($pWords.Count -gt 25) { $pWords = $pWords[0..24] }
     $pixTitle = if ($r.title.Length -gt 100) { $r.title.Substring(0, 100) } else { $r.title }
     $pixDescRaw = if ($r.description) { $r.description } else { $r.title }
     $pixDesc = if ($pixDescRaw.Length -gt 200) { $pixDescRaw.Substring(0, 200) } else { $pixDescRaw }
     $vecteezy += [pscustomobject]@{
       Filename = $r.filename; Title = $title70; Description = $r.description
       Keywords = ($vPhrases -join ", "); License = "free"
       Copyright = $Copyright; Creator = $Creator
     }
     $pixabay += [pscustomobject]@{
       Filename = $r.filename; Title = $pixTitle; Description = $pixDesc
       Keywords = ($pWords -join ", "); Copyright = $Copyright; Creator = $Creator
     }
     ```
     dan inisialisasi `$vecteezy = @(); $pixabay = @()` di baris 339
     (`$adobe = @(); $dream = @()` → tambah keduanya di baris yang sama).
     Nilai `License` adalah literal `"free"` (D2 terkunci; dilarang param baru).
  3. Setelah baris 371–372: tambah
     `$vectCols = @("Filename","Title","Description","Keywords","License","Copyright","Creator")`
     dan `$pixCols = @("Filename","Title","Description","Keywords","Copyright","Creator")`.
     Urutan kolom Vecteezy meniru urutan dokumentasi resmi
     (Filename, Title, Description, Keywords, License, …).
  4. Setelah baris 373–374: tambah dua baris export identik polanya:
     `$vecteezy | Select-Object $vectCols | Export-Csv $VecteezyCsv -Encoding UTF8 -NoTypeInformation`
     dan Pixabay dengan `$pixCols`/`$PixabayCsv`.
  5. Baris 375: ganti return menjadi
     `[pscustomobject]@{ OK = $rows.Count; Failed = $failed; FilteredOut = $filteredOut; Vecteezy = $vecteezy.Count; Pixabay = $pixabay.Count }`.
     Nama `OK/Failed/FilteredOut` dipertahankan (konsumen S2 mencetaknya).
- Urutan perubahan di dalam file: signature → inisialisasi array → blok loop →
  kolom → export → return. Jangan ubah logika `$phrases/$words/$title70/$title200`/stopwords/kategori.
- Behavior yang harus dipertahankan: isi CSV Adobe/Dreamstime byte-identik
  (dibuktikan di test regresi); filter `$OnlyBasenames` berlaku sama untuk
  keempat set (karena memakai `$rows` yang sama); baris tanpa title TIDAK
  di-skip di sini (perilaku hari ini — generator sudah memvalidasi).
- Error handling dan edge case yang harus ditangani:
  `$r.description` kosong → Vecteezy Description kosong (jangan fabrikasi;
  S6 memberi WARN); Pixabay Description fallback ke Title (meniru
  `csv_embed.py:184`); `$phrases` ≤30 / `$words` ≤25 → slicing tidak jalan
  (guard `Count -gt` mencegah `[0..-1]`); `$VecteezyCsv/$PixabayCsv` selalu
  diisi caller (S2 menjamin; tidak perlu guard kosong di v1).
- Test yang harus ditambahkan atau diperbarui: tidak ada Pester di repo untuk
  `*.ps1` — verifikasi fixture terisolasi (pola plan 2026-10-07 Langkah 9):
  dot-source file (aman: baris 945 `if ($MyInvocation.InvocationName -ne ".")`
  mencegah `Main` jalan saat dot-source) lalu panggil fungsi langsung.
- Input test dan expected result: fixture `meta_fix.csv` 4 baris
  (a) success title 40ch + 5 frasa; (b) success title 80ch + 40 frasa;
  (c) skipped minimal; (d) failed. Panggil dengan `$OnlyBasenames=@()`:
  ekspektasi Adobe=3 baris (failed 제외), Dream=3, Vecteezy=3 SEMUA
  `License=free` + baris (b) Title=70ch + keywords=30 frasa,
  Pixabay=3 + baris (b) Title=100ch + keywords≤25 kata. Panggil lagi dengan
  `$OnlyBasenames=@(<2 basename>)` → keempat CSV = 2 baris.
- Command verifikasi yang tersedia di repository (read-only, tanpa ubah repo):
  ```powershell
  powershell -NoProfile -Command "$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Side\Microstock\Orchestrate-Stock.ps1',[ref]$null,[ref]$e); $e.Count"
  # ekspektasi: 0
  Import-Csv .\_t\vect.csv -Encoding UTF8 | Measure-Object  # ekspektasi 3 / 2
  Import-Csv .\_t\vect.csv -Encoding UTF8 | Where-Object { $_.License -ne 'free' }  # ekspektasi: kosong
  ```
  Regresi Adobe/Dream: bangkitkan pasangan CSV dari fungsi LAMA (copy fungsi
  ke file TEMP sebelum edit) vs BARU pada fixture sama, bandingkan dengan
  `Compare-Object (Get-Content a.csv) (Get-Content b.csv)` → ekspektasi: tidak
  ada perbedaan.
- Hasil verifikasi yang diharapkan: parser 0 error; hitungan baris sesuai;
  regresi Adobe/Dream identik.
- Completion criteria: diff terbatas lines 318–376; 5 sub-perubahan di atas
  ada; tidak ada caller yang diubah di langkah ini.
- File atau area yang tidak boleh diubah: situs panggil TAHAP 5/3V (S2),
  direktori/summary (S3/S7), `csv_embed.py` dan seluruh generator, kedua
  script Embed, semua child script, `Process-Batch.ps1`, `.env*`, data.

### S2 — Wire call-site TAHAP 5 + 3V + reuse-tier untuk 2 CSV baru

- Tujuan langkah: CSV Vecteezy/Pixabay benar-benar ditulis tiap run dan ikut
  logika reuse 3-tier (full-reuse/rebuild-API/generate) tanpa stale-SKIP dari
  run lama yang belum punya 2 CSV ini.
- Finding/requirement: F3, F4, F9.
- Dependency: S1 (signature baru). S3–S8 bergantung pada langkah ini.
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:660-667` (TAHAP 5 JPG).
  - `Orchestrate-Stock.ps1:686-720` (TAHAP 3V + Tier1 692–698 + Tier2/3 704–719).
  - `Orchestrate-Stock.ps1:146-164` (`Test-EmbedCsvComplete`), `186-195`
    (`Test-EmbedCsvIdentity`), `307-315` (`Test-EmbedCsvHasColumn`).
- File yang harus diubah: `Orchestrate-Stock.ps1` lines 660–667 dan 686–720 saja.
- Simbol terkait: `$batch/$adobeCsv/$dreamCsv/$genCsv/$haveFinal/$haveSmall/$m`,
  `$reuseFull/$nReuse/$genComplete`, `Test-EmbedCsvComplete/Identity/HasColumn`.
- Kondisi implementasi saat ini: TAHAP 5 membangun 2 path CSV dan memanggil
  5-argumen; 3V Tier1 memeriksa 2 CSV (complete+identity+kolom Category/Filename).
- Perubahan konkret (urutan):
  1. TAHAP 5, setelah baris 662: tambah
     `$vectCsv = Join-Path $metaDir ($batch + "_metadata_vecteezy.csv")` dan
     `$pixCsv = Join-Path $metaDir ($batch + "_metadata_pixabay.csv")`.
  2. Baris 664: ganti call menjadi
     `$m = ConvertTo-EmbedCsvs $genCsv $adobeCsv $dreamCsv $vectCsv $pixCsv $Copyright $Creator $haveFinal`.
  3. Baris 665: ganti pesan menjadi
     `"  Metadata: {0} OK, {1} gagal, {2} tanpa file-output (dilewati), Vecteezy={3}, Pixabay={4} -> {5}" -f $m.OK, $m.Failed, $m.FilteredOut, $m.Vecteezy, $m.Pixabay, $metaDir`.
     Teks `Add-Stage 5` (666) TIDAK diubah.
  4. 3V, setelah baris 689: tambah `$vectCsv`/`$pixCsv` dengan pola nama yang
     SAMA persis seperti butir 1 (agar Tier1 dan rebuild konsisten).
  5. Kondisi `$reuseFull` (692–698): tambah 6 syarat dengan `-and` (jangan ubah
     6 syarat lama):
     `(Test-EmbedCsvComplete $vectCsv $haveSmall)`,
     `(Test-EmbedCsvComplete $pixCsv $haveSmall)`,
     `(Test-EmbedCsvIdentity $vectCsv $Copyright $Creator)`,
     `(Test-EmbedCsvIdentity $pixCsv $Copyright $Creator)`,
     `(Test-EmbedCsvHasColumn $vectCsv "License")`,
     `(Test-EmbedCsvHasColumn $pixCsv "Filename")`.
     Akibat yang disengaja: run lama (hanya Adobe/Dream) GAGAL Tier1 →
     jatuh ke Tier2/3 rebuild (bukan SKIP basi). Ini perilaku yang benar.
  6. Baris 703 `$m = [pscustomobject]@{...}` (cabang reuse): tambah
     `Vecteezy = $nReuse; Pixabay = $nReuse`.
  7. Baris 716: ganti call seperti butir 2 (dengan `$haveSmall`).
     Baris 717: ganti pesan seperti butir 3.
- Behavior yang dipertahankan: Tier2 vs Tier3 (lengkap-mentah vs generate API),
  `-Force` bypass, `throw` bila `$m.OK -eq 0`, teks stage, backend `api` (909).
- Error handling/edge: `$haveSmall` kosong → `Test-EmbedCsvComplete` false
  (baris 151) → Tier3, seperti hari ini; 4 CSV ditulis atomis oleh
  `Export-Csv` (tulis-penuh; tidak ada partial-CSV).
- Input test dan expected result:
  (i) fixture dengan Adobe+Dream lengkap TAPI tanpa vecteezy/pixabay →
  3V TIDAK SKIP (membangun ulang, pesan "rebuild…tanpa API" bila
  `metadata.csv` lengkap); (ii) setelah run penuh → rerun tanpa `-Force` →
  3V `SKIP … reuse`; (iii) `Import-Csv` vecteezy: semua `License=free`,
  ada kolom `License`; pixabay ada kolom `Filename`.
- Command verifikasi: `Import-Csv <meta>\*_metadata_vecteezy.csv | Select-Object -First 1 | Format-List *`
  (ekspektasi kolom Filename/Title/Description/Keywords/License/Copyright/Creator);
  `echo $LASTEXITCODE` run fixture (ekspektasi 0 bila tahap lain OK/PARTIAL).
- Completion criteria: kedua call-site mem passing 7-argumen; Tier1 berisi
  12 syarat total; tidak ada perubahan teks stage/summary.
- Tidak boleh diubah: `ConvertTo-EmbedCsvs` isi (S1), generator `run.bat`,
  TAHAP 4/4V/5V/6V, embed, direktori.

### S3 — Direktori + packaging foto JPG (Vecteezy photo + Pixabay photo)

- Tujuan langkah: run `Target=JPG` menghasilkan `for_vecteezy_photo/` dan
  `for_pixabay_photo/` berisi JPG ter-embed + salinan CSV, memakai script
  Embed yang ada tanpa modifikasi.
- Finding/requirement: F1, F5 (EXIF), F8, F9.
- Dependency: S2 (variabel `$vectCsv/$pixCsv` TAHAP 5 tersedia dalam scope
  `Process-Dir`).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:416-440` (definisi + pembuatan direktori).
  - `Orchestrate-Stock.ps1:669-678` (TAHAP 6).
  - `Embed-JpgMetadata.ps1:229-249` (reset 2-fase + tulis; bukti EXIF lain
    dipertahankan — reset hanya tag Title/Description/Keywords/Rights/Creator,
    flag `-P` menjaga timestamp, `-m` mengabaikan minor; pahami, jangan ubah).
- File yang harus diubah: `Orchestrate-Stock.ps1` lines 427–440 dan 669–678 saja.
- Simbol terkait: `$stock/$final/$metaDir/$forAdobe/$forDream`,
  `Invoke-Child`, `$nA/$nD`, `Embed-JpgMetadata.ps1`.
- Kondisi saat ini: 4 direktori paket Adobe/Dream battre; TAHAP 6 embed 2 CSV.
- Perubahan konkret (urutan):
  1. Setelah blok `if ($Target...)` (setelah baris 437, sebelum `foreach`
     baris 438): tambah
     `$forVectPhoto = Join-Path $stock "for_vecteezy_photo"`,
     `$forPixPhoto = Join-Path $stock "for_pixabay_photo"`,
     `$forVectEps = Join-Path $stock "for_vecteezy_eps"`,
     `$forPixSvg = Join-Path $stock "for_pixabay_svg"`.
     (Keempatnya didefinisikan di sini agar S4 tidak perlu edit blok ini lagi.)
  2. Baris 438: tambah keempat variabel ke array `foreach` pembuatan direktori.
  3. TAHAP 6, setelah baris 674 (Dream embed): tambah dua blok pola IDENTIK:
     `$code = Invoke-Child ... "Embed-JpgMetadata.ps1" @{ CsvPath = $vectCsv; JpgDir = $final; OutDir = $forVectPhoto }`
     `if ($code -ne 0) { Write-Host "  [!] Embed Vecteezy sebagian gagal (exit $code), lanjut." ... Yellow }`
     dan sama untuk `$pixCsv`/`$forPixPhoto` ("Pixabay").
     `Embed-JpgMetadata.ps1` menerima kolom CSV apa pun selama ada
     Title/Description/Keywords/Copyright/Creator (baris 217–224: kolom
     `License` ekstra diabaikan otomatis oleh `Import-Csv`); ambang warning
     Adobe (>70/>49) tidak dipicu karena CSV sudah di-cap di S1 — tidak perlu
     ubah script Embed (sengaja).
  4. Baris 675–676: tambah `$nV`/`$nP` (hitung `*.jpg` di 2 dir baru, pola sama).
     Baris 677–678: ganti pesan/detail menjadi
     `"  Siap upload: Adobe={0}, Dreamstime={1}, Vecteezy={2}, Pixabay={3}."`
     dan `Add-Stage 6 "Embed" "OK" "Adobe=$nA, Dreamstime=$nD, Vecteezy=$nV, Pixabay=$nP"`.
     Nomor stage (6) dan judul ("Embed") WAJIB tetap.
- Behavior yang dipertahankan: embed Adobe/Dream baris 671–674 tidak tersentuh;
  pola yellow-lanjut (tanpa throw, tanpa `failed_*.txt` untuk embed —
  konsisten dengan yang ada); sumber `$final` tidak diubah (Embed menyalin).
- Kepatuhan EXIF Pixabay (F5, tanpa kode): reset 2-fase hanya menyentuh tag
  metadata deskriptif; EXIF lain (Software/generator/kamera) dipertahankan —
  memenuhi maksud "jangan ubah/strip EXIF" untuk pengungkapan AI. Dilarang
  menambah flag strip (`-all=`, `-exif:all=`) di langkah mana pun.
- Edge: `$m.OK -eq 0` sudah throw di TAHAP 5 → TAHAP 6 tidak jalan dengan CSV
  kosong; rerun skip-valid via Embed (file ada → SKIP di dalam script Embed).
- Input test dan expected result: fixture 3 JPG final + 4 CSV 3-baris →
  `for_vecteezy_photo`=3 JPG, `for_pixabay_photo`=3 JPG; baca-balik
  `exiftool -s -s -s -XMP-dc:Title` pada 1 sampel = Title CSV; salinan CSV ada
  di tiap dir paket.
- Command verifikasi:
  `(Get-ChildItem <pkg> -Filter *.jpg).Count  # ekspektasi 3 dan 3`
  `& 'C:\Apps\exiftool\exiftool.exe' -s -s -s -XMP-dc:Title <sampel>  # ekspektasi = Title CSV`
- Completion criteria: 2 dir baru terisi; Adobe/Dream counts tak berubah;
  tidak ada edit di `Embed-JpgMetadata.ps1`.
- Tidak boleh diubah: `Embed-JpgMetadata.ps1`, baris Adobe/Dream, logika convert.

### S4 — Packaging vektor (Vecteezy EPS + Pixabay SVG, guard per-Target)

- Tujuan langkah: run vektor menghasilkan paket kind-pure tanpa mencampur
  `.svg`/`.eps`: `Target=EPS` → `for_vecteezy_eps` (pasangan JPG+EPS) DAN
  `for_pixabay_svg` (pasangan JPG+SVG dari `svgDir` yang pasti ada);
  `Target=SVG` → hanya `for_pixabay_svg` + pesan skip Vecteezy yang eksplisit.
- Finding/requirement: F2, F5, F8, F9.
- Dependency: S2 (CSV), S3 (direktori sudah dibuat).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:778-829` (TAHAP 6V + 7V penuh).
  - `Embed-VectorMetadata.ps1:296-355` (pairing basename + reset XMP-dc EPS /
    injeksi XML SVG + baca-balik; pahami, jangan ubah).
- File yang harus diubah: `Orchestrate-Stock.ps1` lines 810–829 saja
  (blok 7V; loop stale-cleanup 815–819 TIDAK disentuh — dir baru kind-pure
  by-construction sehingga tidak butuh cleanup).
- Simbol terkait: `$vecSrc/$vecKind/$vecFilter/$svgDir/$epsDir/$prevDir`,
  `$adobeCsv/$dreamCsv/$vectCsv/$pixCsv`, `$forVectEps/$forPixSvg`,
  `Embed-VectorMetadata.ps1`.
- Kondisi saat ini: 7V meng-embed Adobe+Dream via `JpgDir=$prevDir`,
  `VecDir=$vecSrc` (svgDir untuk Target SVG; epsDir untuk Target EPS).
- Perubahan konkret (urutan, setelah baris 825, sebelum hitung 826):
  1. Tambah blok Pixabay-SVG (jalan di Target SVG DAN EPS karena `svgDir`
     selalu ada di kedua jalur — 6V hanya menambah epsDir):
     ```powershell
     $vemb = @{ CsvPath = $pixCsv; JpgDir = $prevDir; VecDir = $svgDir; OutDir = $forPixSvg; VecKind = "svg" }
     $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-VectorMetadata.ps1") $vemb
     if ($code -ne 0) { Write-Host "  [!] Embed Pixabay-SVG sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
     ```
  2. Tambah blok Vecteezy-EPS dengan guard:
     ```powershell
     if ($vecKind -eq "eps") {
       $vemb = @{ CsvPath = $vectCsv; JpgDir = $prevDir; VecDir = $epsDir; OutDir = $forVectEps; VecKind = "eps" }
       $code = Invoke-Child (Join-Path $PSScriptRoot "Embed-VectorMetadata.ps1") $vemb
       if ($code -ne 0) { Write-Host "  [!] Embed Vecteezy-EPS sebagian gagal (exit $code), lanjut." -ForegroundColor Yellow }
     } else {
       Write-Host "  Vecteezy vector skip (butuh EPS; jalankan Target=EPS)." -ForegroundColor Gray
     }
     ```
     (`VecDir=$epsDir` eksplisit, bukan `$vecSrc`, agar niat terbaca.)
  3. Hitung: `$nVV` (pakai `$vecFilter`? TIDAK — `$vecFilter` mengikuti Target;
     gunakan filter eksplisit: `*.eps` di `$forVectEps`, `*.svg` di
     `$forPixSvg`) dan baris 828–829 menjadi
     `"  Siap upload: Adobe={0}, Dreamstime={1}, Vecteezy-EPS={2}, Pixabay-SVG={3} (pasangan JPG+vektor)."`
     + `Add-Stage 7 "Embed vektor" "OK" "Adobe=$nA, Dreamstime=$nD, VectEPS=$nVV, PixSVG=$nPV"`.
     Nomor (7) + judul ("Embed vektor") tetap.
- Behavior yang dipertahankan: dua vemb Adobe/Dream (820–825) tak tersentuh;
  pasangan JPG+vektor basename-sama; CSV pendamping disalin (oleh script
  Embed, baris 354–357); yellow-lanjut tanpa throw.
- Edge: Target SVG → `$forVectEps` tetap kosong (dibuat S3 tapi tak diisi —
  ekspektasi, bukan bug); Target EPS → kedua dir terisi; rerun skip-valid di
  dalam script Embed; `VecKind` salah → script Embed memvalidasi
  (`ValidateSet`) dan return non-zero → tertangani pola lanjut.
- Input test dan expected result:
  SVG-target (2 SVG + preview): `for_pixabay_svg` = 2 `.svg` + 2 `.jpg`,
  pesan skip Vecteezy muncul, verifikasi SVG `<title>` = Title CSV;
  EPS-target: `for_vecteezy_eps` = 2 `.eps` + 2 `.jpg` (baca-balik
  `XMP-dc:Title` OK), `for_pixabay_svg` = 2+2.
- Command verifikasi:
  `(Get-ChildItem $forVectEps -Filter *.eps).Count  # EPS-run ekspektasi 2`
  `& 'C:\Apps\exiftool\exiftool.exe' -s -s -s -XMP-dc:Title <sampel.eps>  # = Title CSV`
- Completion criteria: matriks Target di atas terpenuhi; Adobe/Dream counts tak berubah.
- Tidak boleh diubah: `Embed-VectorMetadata.ps1`, vemb Adobe/Dream, stale-loop,
  6V/5V/4V.

### S5 — Sanitasi nama file Vecteezy + rewrite CSV paket

- Tujuan langkah: paket Vecteezy memenuhi aturan "Filename tanpa spasi"
  (syarat FTP; Add Data juga menerima) sambil menjaga 1-korespondensi
  CSV↔disk, tanpa menyentuh sumber/`$metaDir`/paket Adobe/Dream/Pixabay.
- Finding/requirement: F3 (Filename), F9.
- Dependency: S3, S4 (paket sudah ada).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:128-138` (`Get-NormBase` — pola basename).
  - `Orchestrate-Stock.ps1:669-678` dan `810-829` (titik sisip pemanggilan).
- File yang harus diubah: `Orchestrate-Stock.ps1`: (a) 2 fungsi baru setelah
  `Get-NormBase` (sebelum `Get-CsvSourceFile` ~baris 140); (b) 2 situs panggil
  (akhir TAHAP 6 JPG + akhir 7V cabang EPS).
- Simbol terkait: `Get-NormBase`, `Import-Csv/Export-Csv`, `Move-Item`.
- Kondisi saat ini: tidak ada sanitasi; nama paket = nama sumber
  (bisa mengandung spasi, `…`, `__`, flera titik).
- Perubahan konkret (urutan):
  1. Fungsi `Get-SafeUploadName([string]$basename)`:
     `$s = $basename -replace "[^\w\-]+","_"; $s = $s -replace "_+","_"; $s = $s.Trim("_","-","."); if ([string]::IsNullOrWhiteSpace($s)) { $s = "file" }; return $s`.
     (`\w` .NET mempertahankan huruf Unicode; elipsis/non-ASCII yang
     menimbulkan warning ExifTool jinak tetap dipertahankan — konsisten
     dengan perilaku Embed yang ada.)
  2. Fungsi `Repair-VecteezyPackage([string]$PkgDir, [string]$CsvFileName)`:
     enumerasi file `Sort-Object Name`; petakan basename→aman-unik
     (tabrakan → tambah `_2`, `_3`… deterministik sesuai urutan sort);
     `Move-Item -LiteralPath` tiap file; lalu rewrite SALINAN CSV di dalam
     `$PkgDir` (bukan `$metaDir`): cocokkan baris via `Get-NormBase` atas
     kolom `Filename` LAMA ke basename lama, tulis `Filename` BARU TANPA
     ekstensi (syarat FTP; Add Data menerima tanpa ekstensi per dokumentasi),
     kolom lain byte-sama; tulis UTF8 NoTypeInformation; `Write-Host` kuning
     tiap rename (`"  Sanitasi: <lama> -> <baru>"`); seluruh badan
     try/catch → warning + return `$false` (tidak pernah throw).
  3. Panggil di akhir TAHAP 6 (setelah hitung `$nV`):
     `Repair-VecteezyPackage $forVectPhoto (Join-Path $forVectPhoto ((Get-Item $vectCsv).BaseName + ".csv"))`
     — nama salinan CSV = basename CSV sumber (pola script Embed yang menyalin
     CSV ke OutDir). Bungkus: `try { ... } catch { Write-Host "  [!] Sanitasi Vecteezy-photo gagal, lanjut." Yellow }`.
     Panggil kedua di 7V HANYA dalam guard `$vecKind -eq "eps"` untuk
     `$forVectEps` dengan pola sama. Pixabay/Adobe/Dream TIDAK disanitasi.
- Behavior yang dipertahankan: isi file tak berubah (rename saja); CSV
  `$metaDir` tak berubah; idempoten (rerun: nama sudah aman → tidak ada rename;
  pemetaan stabil karena sort + suffix deterministik).
- Edge: dua nama berbeda menjadi sama setelah sanitasi (`"a b"` vs `"a_b"`) →
  `_2` (WARN kuning); basename kosong setelah trim → `"file"` (+suffix bila
  perlu); CSV paket yang hilang (embed gagal total) → return false + warning,
  bukan FATAL.
- Input test dan expected result: paket berisi `001_a b.jpg`, `001_a_b.jpg`,
  `002_x….jpg` → setelahnya `001_a_b.jpg`, `001_a_b_2.jpg`, `002_x_.jpg`
  (atau setara deterministik); CSV `Filename` = basename-baru tanpa ekstensi,
  cocok 1:1 dengan `Get-ChildItem -File | % BaseName`; kolom Title/Keywords
  tak berubah (spot-check 1 baris).
- Command verifikasi:
  `Compare-Object ((Import-Csv <pkgcsv>).Filename | Sort-Object) ((Get-ChildItem <pkg> -File -Filter *.jpg | % BaseName) | Sort-Object)`
  ekspektasi: tidak ada perbedaan. Rerun perintah sama → tidak ada rename
  kedua (bukti idempoten dari transcript).
- Completion criteria: perbandingan di atas kosong; Adobe/Dream/Pixabay tak tersentuh.
- Tidak boleh diubah: sumber, `$metaDir`, paket non-Vecteezy, script Embed.

### S6 — Laporan validasi warn-only `validation_vecteezy_pixabay.txt`

- Tujuan langkah: tiap run menulis laporan kesiapan-upload yang jujur
  (WARN, bukan block) sehingga kegagalan portal (MP/ukuran/sRGB/judul duplikat/
  keyword) tertangkap SEBELUM upload manual, tanpa melanggar partial-tolerance.
- Finding/requirement: F1, F2, F3, F6, F7 (ambang), F9 (warn-only).
- Dependency: S3, S4, S5 (paket final yang divalidasi).
- File yang harus dibaca:
  - `Orchestrate-Stock.ps1:390-406` (`Restore-OrphanTmps` — titik sisip fungsi
    baru setelahnya).
  - Pola validasi yang ditiru (baca, jangan ubah):
    `Convert-PngToJpg.ps1:85-124` (`Test-ImageComplete`/`Test-MediaOk`),
    `Convert-SvgToEps.ps1:42-51` (`Test-EpsOk`), `Trace-Svg.ps1:56-65`
    (`Test-SvgOk`), `Embed-VectorMetadata.ps1:122-138` (magic-check).
- File yang harus diubah: `Orchestrate-Stock.ps1`: (a) fungsi baru
  `Test-UploadReadiness` setelah `Restore-OrphanTmps`; (b) 2 situs panggil
  (akhir TAHAP 6 cabang JPG + akhir 7V) + 1 baris cetak summary.
- Simbol terkait: `ffprobe`, `ExifTool ($BinExif)`, `Get-Item Length`,
  `Import-Csv`, stage `Add-Stage` (TIDAK dipakai di sini — validasi bukan stage).
- Kondisi saat ini: tidak ada validasi kesiapan; satu-satunya gate adalah
  keberhasilan teknis per-file.
- Perubahan konkret — fungsi `Test-UploadReadiness([string]$StockDir, [hashtable]$Packages)`:
  `$Packages` memetakan label → `@{Dir; Csv; Kind}` dengan Kind ∈
  `photo|eps|svg`. Untuk tiap file per paket (try/catch per file, kumpulkan
  string WARN; fungsi tidak pernah throw):
  V1 integritas: JPG SOI/EOI + `ffprobe -v error -select_streams v:0` exit 0
  (pola Convert-PngToJpg); EPS header `%!PS`; SVG head `<svg`.
  V2 dimensi via `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0`
  → MP=`w*h`: photo syarat 4.000.000–50.000.000; paket vektor memakai JPG
  preview PENDAMPING basename-sama sebagai proksi (keterbatasan OQ-3 —
  tulis di laporan: `"MP vektor = proksi preview JPG"`); syarat 4.000.000–
  25.000.000; contoh pemicu: preview 6000×6000=36MP → WARN (benar, bukan bug).
  V3 ukuran 1MB–50MB (`(Get-Item).Length`).
  V4 sRGB warn-only: `ExifTool -s -s -s -ColorSpace/-ProfileDescription`;
  bila tak terbaca/tak mengandung `sRGB` → WARN "sRGB tak terkonfirmasi"
  (DILARANG auto-convert — OQ-4).
  V6 CSV: judul duplikat (`Group-Object Title | Where Count -gt 1` → WARN per
  judul); Vecteezy keywords per baris 1–30 (0/>30 WARN; <10 INFO
  "disarankan ≥10"); Title Vecteezy ≤70 / Pixabay ≤100 / Description ≤200 WARN;
  `Filename` cocok dengan basename disk (extensionless, case-insensitive) +
  cocok pola `^[\w\-]+$` (spasi → WARN); seluruh `License` Vecteezy = `free`.
  V7 pengingat manual (selalu ditulis di ekor laporan): centang AI-generated
  Pixabay; pastikan tanpa orang nyata/merek/gaya-artist; atribusi wajib untuk
  lisensi free Vecteezy; FTP tanpa ekstensi vs Add Data bebas.
  Tulis (overwrite) `$StockDir/validation_vecteezy_pixabay.txt` UTF8:
  header waktu + Target, per-paket counts, daftar WARN (atau "0 WARN"),
  checklist manual. Return jumlah WARN (int). Situs panggil:
  `try { $w = Test-UploadReadiness $stock <paket-cabang-ini>; Write-Host ("  Validasi: {0} WARN -> {1}" -f $w, (Join-Path $stock "validation_vecteezy_pixabay.txt")) Gray } catch { Write-Host "  [!] Validasi gagal (non-fatal), lanjut." Yellow }`.
- Behavior yang dipertahankan: tidak ada throw/gate baru; exit-code dan stage
  tak dipengaruhi hasil validasi; laporan di-overwrite tiap run (deterministik).
- Edge: `ffprobe`/ExifTool hilang → semua cek terkait menjadi WARN tunggal
  "tool hilang", bukan error; CSV paket hilang → seksi "CSV tak ditemukan
  (WARN)" + lanjut; preview pendamping hilang untuk V2 vektor → WARN, bukan FATAL.
- Input test dan expected result: fixture 2 baik + 1 JPG <4MP + 1 baris CSV
  judul-duplikat + 1 baris keywords 35 frasa → laporan memuat 4 kelas WARN
  (MP, judul duplikat, keyword>30, + sRGB bila tak terkonfirmasi); counts
  paket TETAP (bukti warn-only); file laporan ada di `_stock/`.
- Command verifikasi:
  `Get-Content <_stock>\validation_vecteezy_pixabay.txt  # ekspektasi: seksi per paket + WARN`
  `(Get-ChildItem <pkg> -Filter *.jpg).Count  # ekspektasi tak berubah vs pra-validasi`
- Completion criteria: laporan ada tiap run cabang; 0 pengaruh ke counts/exit.
- Tidak boleh diubah: ambang agensi lain, logika packaging, script Embed,
  aturan exit.

### S7 — Summary + return object (path upload baru)

- Tujuan langkah: operator melihat 4 path baru di ringkasan + konsumen
  programatik (rekap antrean) mendapat properti baru tanpa merusak形状 lama.
- Finding/requirement: F8, F9.
- Dependency: S3–S6.
- File yang harus dibaca: `Orchestrate-Stock.ps1:835-874` (finally/summary/
  return) + `927-942` (rekap + exit).
- File yang harus diubah: `Orchestrate-Stock.ps1` lines 860–874 saja.
- Simbol terkait: `$forAdobe/$forDream/$forVectPhoto/$forPixPhoto/$forVectEps/$forPixSvg`,
  `$script:stages`, return `@{Dir,Status,Adobe,Dream,Waktu}`.
- Kondisi saat ini: mencetak `Upload Adobe/Dream` (861–862); return 5 properti.
- Perubahan konkret (urutan):
  1. Setelah baris 862: tambah cetak Target-aware (tanpa mengubah 2 baris lama):
     cabang JPG → `"   Upload Vecteezy: {0}" -f $forVectPhoto` +
     `"   Upload Pixabay : {0}" -f $forPixPhoto`;
     cabang SVG → Pixabay-SVG saja + baris Vecteezy "(n/a — butuh Target=EPS)";
     cabang EPS → Vecteezy-EPS + Pixabay-SVG.
     Implementasi: `if ($Target -eq "JPG") {...} elseif ($Target -eq "SVG") {...} else {...}`
     memakai variabel yang didefinisikan S3 (selalu ada).
  2. Return 870–874: tambah `Vecteezy = <string|string[]>; Pixabay = <string|string[]>`
     (isi = path dir yang relevan per Target; cabang lain = `"-"`), nama lama
     (`Dir/Status/Adobe/Dream/Waktu`) dan urutannya tetap.
- Behavior yang dipertahankan: format tabel stage, warna, aturan
  PARTIAL/FATAL, blok pemulihan, loop rekap antrean (932–937 hanya memakai
  Dir/Status — tidak diubah), aturan exit 941–942.
- Edge: variabel dir selalu terdefinisi (S3 membuatnya unconditional) → tidak
  ada `$null` di summary; run lama tanpa paket baru (tidak mungkin pasca-S3,
  tapi bila CSV kosong → path tetap dicetak + counts 0 — jujur, bukan error).
- Input test dan expected result: run fixture JPG → transcript memuat
  `Upload Vecteezy:` + `Upload Pixabay :`; return object
  `.Vecteezy -ne $null`; `echo $LASTEXITCODE` tak berubah vs perilaku lama
  (0 untuk OK/PARTIAL-murni).
- Command verifikasi: inspeksi transcript `orchestrator.log`
  (`Select-String "Upload Vecteezy"` → ekspektasi ≥1 hit).
- Completion criteria: 2 baris summary baru per Target + 2 properti return;
  nol perubahan stage/exit.
- Tidak boleh diubah: selain lines 860–874 (khususnya loop stage, Main, exit).

### S8 — Verifikasi fixture ujung-ke-ujung E1–E8 (tanpa ubah repo)

- Tujuan langkah: buktikan tiap finding tertutup (F1–F10) dan F9 tidak regresi,
  tanpa test harness baru.
- Finding/requirement: semua (verifikasi akhir).
- Dependency: S1–S7 selesai.
- File yang harus dibaca: tidak ada file baru; fixture di
  `C:\Users\alama\AppData\Local\Temp\opencode\plan-verify-vp\` (buat saat
  verifikasi, HAPUS setelah selesai — bukan bagian repo, mengikuti preseden
  plan 2026-10-07).
- File yang harus diubah: TIDAK ADA (langkah verifikasi saja).
- Kasus uji (wajib, urut; E4 memakai `-Scale 2` agar cepat — preseden P4):
  - E1 JPG penuh: 3 image valid (1 nama ber-spasi) → ekspektasi 4 CSV
    3-baris; `for_adobe/for_dreamstime/for_vecteezy_photo/for_pixabay_photo`
    = 3 JPG tiap dir; CSV Vecteezy `License`=free semua + Filename tanpa spasi;
    laporan validasi ada; `exit 0`.
  - E2 rerun idempoten: perintah SAMA tanpa `-Force` → semua tahap SKIP,
    counts identik, sanitasi tidak rename ulang, `exit 0`.
  - E3 partial: 1 PNG korup di sumber → ≥1 stage PARTIAL + `failed_*.txt`
    1 baris; keempat CSV = 2 baris (yang gagal terfilter via `$haveFinal`);
    paket baru = 2 file; `exit 0` (PARTIAL-murni).
  - E4 SVG-target (2 valid + 1 korup): trace PARTIAL; `for_pixabay_svg` =
    2 svg + 2 jpg; pesan skip Vecteezy; `exit 0`.
  - E5 EPS-target (2 valid): `for_vecteezy_eps` = 2 eps + 2 jpg (baca-balik
    XMP Title OK) + `for_pixabay_svg` = 2+2; `exit 0`.
  - E6 stres metadata: title 80ch + 40 frasa → Vecteezy Title 70 + 30 frasa,
    Pixabay Title ≤100 + ≤25 kata, License=free.
  - E7 recovery: hapus/perbaiki file gagal E3 → rerun → counts menjadi 3,
    tanpa duplikasi.
  - E8 syntax: parser check `Orchestrate-Stock.ps1` → 0 error.
- Command verifikasi (contoh; sesuaikan nama fixture):
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Orchestrate-Stock.ps1 -SourceDir <fix> -Target JPG
  echo $LASTEXITCODE  # ekspektasi 0 untuk E1/E3/E4/E5 (PARTIAL-murni)
  (Get-ChildItem <_stock>\for_vecteezy_photo -Filter *.jpg).Count  # E1=3, E3=2
  Import-Csv <meta>\*_metadata_vecteezy.csv -Encoding UTF8 | Where-Object { $_.License -ne 'free' }  # ekspektasi kosong
  Compare-Object ((Import-Csv <pkgcsv>).Filename | Sort-Object) ((Get-ChildItem <pkg> -File -Filter *.jpg | % BaseName) | Sort-Object)  # ekspektasi kosong (S5)
  Get-Content <_stock>\validation_vecteezy_pixabay.txt  # ekspektasi ada
  & 'C:\Apps\exiftool\exiftool.exe' -s -s -s -XMP-dc:Title <sampel.eps>  # E5 = Title CSV
  ```
- Hasil yang diharapkan: sesuai tiap kasus; `git status --porcelain` hanya
  `M Orchestrate-Stock.ps1` (+ file plan ini) — tanpa fixture, tanpa `_stock`,
  tanpa `.env`.
- Completion criteria: E1–E3 + E5–E8 lulus wajib; E4 boleh SKIP sekali dengan
  alasan mesin (upscale/trace lambat) selain itu wajib lulus.
- Tidak boleh diubah: file repo mana pun selama verifikasi kecuali perbaikan
  bug yang ditemukan (masuk sebagai revisi S1–S7, bukan edit diam-diam).

## Risks

- R1: EPS Inkscape belum tentu lolos validasi Illustrator-10 Vecteezy (B1).
  Mitigasi: v1 warn-only + uji upload manual 1–3 file di S8; jangan jadikan gate.
- R2: preview 6000px untuk gambar near-square menghasilkan MP proksi >25MP
  (contoh 6000×6000=36MP) → WARN benar. Mitigasi: label proksi eksplisit di
  laporan (OQ-3); dilarang auto-resize.
- R3: divergensi Python (`VECTEEZY_MAX_TAGS=50`, tanpa License) vs PS (30 +
  License). Mitigasi: PS-only di v1 (D4) + OQ-1/OQ-2; dilarang sync diam-diam.
- R4: tabrakan sanitasi (`"a b"` vs `"a_b"`). Mitigasi: suffix `_2` deterministik
  + rewrite CSV + WARN (S5).
- R5: model kecil salah positional-arg / rename stage / ubah Embed.
  Mitigasi: anchor baris eksak + daftar larangan per langkah + S8 `git status`.
- R6: ekspektasi "otomatisasi penuh Pixabay" — mustahil (checkbox AI +
  tagging manual). Mitigasi: CSV pendamping + checklist di laporan (S6/S8).

## Progress Log

- 2026-10-10 00:00:00 — Plan dibuat dari riset help-center Vecteezy/Pixabay +
  inspeksi `Orchestrate-Stock.ps1:47-945`, `Embed-JpgMetadata.ps1:1-278`,
  `Embed-VectorMetadata.ps1:1-367`, `Trace-Svg.ps1`, `Export-VectorPreview.ps1`,
  `Convert-SvgToEps.ps1`, `Convert-PngToJpg.ps1`, `Convert-WebpToJpg.ps1`,
  `csv_embed.py:1-220`. Belum ada implementasi. Keputusan terkunci D1–D7.
- 2026-10-10 22:48:00 — Implementasi S1–S8 selesai penuh pada `Orchestrate-Stock.ps1`.
  (1) `ConvertTo-EmbedCsvs` emit 4 CSV (Adobe, Dreamstime, Vecteezy `License=free`, Pixabay).
  (2) Wire call-site TAHAP 5 & 3V + reuse-tier 12 syarat.
  (3) Packaging foto JPG untuk `for_vecteezy_photo` dan `for_pixabay_photo`.
  (4) Packaging vektor `for_vecteezy_eps` (guard EPS) dan `for_pixabay_svg`.
  (5) Sanitasi nama file Vecteezy via `Get-SafeUploadName` & `Repair-VecteezyPackage` + rewrite CSV paket.
  (6) Laporan validasi kesiapan upload `validation_vecteezy_pixabay.txt` via `Test-UploadReadiness` (warn-only).
  (7) Summary upload path Vecteezy & Pixabay + return object properties.
  (8) Verifikasi parsial dan ujung-ke-ujung (parser 0 error, regresi CSV, sanitasi idempoten, fixture EPS end-to-end exit 0).

## Notes

- Keputusan desain final (implementer dilarang mengubah):
  4 dir kind-pure (D7) meniru konvensi `for_adobe_svg/for_adobe_eps` yang ada
  (`Orchestrate-Stock.ps1:427-437`) — menghindari campuran `.svg`/`.eps` dan
  kebutuhan stale-cleanup baru. Pixabay-SVG diambil dari `svgDir` di kedua
  run vektor (EPS-run selalu men-trace dulu); Vecteezy-EPS hanya di EPS-run.
  `License` literal `"free"` (D2) — tanpa param agar tidak ada jalan
  mengaktifkan `pro`/`editorial` diam-diam. Validasi warn-only (D6).
- Deviasi dari sketsa diskusi awal: nama `for_vecteezy_vector` dibatalkan
  menjadi `for_vecteezy_eps` + `for_pixabay_svg` (alasan di atas).
- Checklist upload manual (tulis juga di ekor laporan S6):
  Pixabay — centang `AI-generated`, pastikan tanpa orang nyata/merek/gaya
  artist, kurasi (jangan upload near-identical massal), tag manual dari CSV
  pendamping. Vecteezy — lisensi free wajib atribusi di produk akhir;
  FTP: CSV tanpa ekstensi; Add Data: dengan/tanpa ekstensi OK.
- Kepatuhan EXIF Pixabay: tidak ada flag strip di plan ini; reset Embed hanya
  menyentuh tag deskriptif + `-P` menjaga timestamp — EXIF generator/kamera
  dipertahankan.
- Area yang TIDAK BOLEH diubah plan ini (global, mengikat semua langkah):
  `Embed-JpgMetadata.ps1`, `Embed-VectorMetadata.ps1`, `Convert-PngToJpg.ps1`,
  `Convert-WebpToJpg.ps1`, `Upscale.ps1`, `Trace-Svg.ps1`,
  `Export-VectorPreview.ps1`, `Convert-SvgToEps.ps1`, `Rename-Numbered.ps1`,
  `Process-Batch.ps1`, `microstock-metadata-generator/**`, `.env*`,
  `AGENTS.md`, data sampel/batch (`*_2610*/**`, `gemini_*/**`, `*_stock/**`
  mana pun), `plans/**` lain, `.memory/**`.
- Blocker B1: kompatibilitas EPS-Inkscape vs Illustrator-10 tidak dapat
  diverifikasi statis. Opsi: (a) warn-only + uji upload manual 1–3 file
  [REKOMENDASI, dipakai v1]; (b) jadikan gate block packaging [DITOLAK —
  melanggar D6/partial-tolerance]; (c) beli/validasi via Illustrator
  [di luar scope].
- Open questions (diputuskan sementara untuk v1, jangan pilih diam-diam):
  - OQ-1 cap keyword Vecteezy 30 vs `VECTEEZY_MAX_TAGS=50` (jalur video):
    v1 pakai 30 (dokumen kontributor resmi); follow-up: selaraskan konstanta
    Python + uji unggah.
  - OQ-2 divergensi Python (tanpa License di `VECTEEZY_COLUMNS`, image-path
    tanpa vecteezy/pixabay): v1 PS-only (D4); follow-up: putuskan single-source
    (Python sebagai sumber + PS memanggilnya) atau dual-write terdokumentasi.
  - OQ-3 MP vektor via proksi preview-JPG (bounding-box EPS tidak di-parse):
    v1 proksi + label; follow-up: parse `/BoundingBox`/`HiResBoundingBox`.
  - OQ-4 sRGB: v1 warn-only; follow-up: konversi `-colorspace sRGB` + ICC
    (mengubah piksel — butuh persetujuan).
  - OQ-5 Pixabay tanpa CSV-upload: v1 CSV pendamping copy-paste; tidak ada
    otomatisasi lebih jauh yang aman.

## Handoff Checklist (untuk model implementer kecil)

- [ ] Baca blok baris eksak tiap langkah sebelum mengedit; ikuti urutan
  sub-perubahan; jangan refactor di luar anchor.
- [ ] Pertahankan nama stage, nomor stage, teks `Add-Stage` lama, aturan
  PARTIAL/FATAL/exit, dan perilaku Adobe/Dream (bukti regresi S1).
- [ ] Jangan sentuh daftar global "TIDAK BOLEH diubah"; jangan tambah
  dependency/binary/param baru (khususnya tanpa param License).
- [ ] Jangan perkenalkan `exit 2`, gate throw baru, atau flag strip-EXIF.
- [ ] Jalankan E1–E8 sesuai urutan; catat SKIP hanya yang diizinkan + alasan.
- [ ] Fixture hanya di TEMP (`plan-verify-vp\`), hapus setelah selesai.
- [ ] `git status --porcelain` akhir: `M Orchestrate-Stock.ps1` + file plan ini
  saja. Jangan stage/commit apa pun.
- [ ] Bila temukan bug baru: hentikan, catat sebagai temuan baru + OQ/B baru,
  jangan perluas scope diam-diam.

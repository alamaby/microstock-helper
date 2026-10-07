# Microstock — Instruksi Agent Lokal

## Upscayl CLI (upscale image, terverifikasi 2026-10-03)

Binary: `C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe` (Upscayl 2.15.0, wrapper `realesrgan-ncnn-vulkan`).
Model dir: `C:\Program Files\Upscayl\resources\models`. Model standard: `upscayl-standard-4x` (file `upscayl-standard-4x.bin/.param`, skala native 4x).

### Perintah upscale 5x model standard

```powershell
& "C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe" `
  -i input.png -o output.png `
  -m "C:\Program Files\Upscayl\resources\models" `
  -n upscayl-standard-4x -z 4 -s 5 -f png -v
```

Catatan:
- `-z` = skala model (wajib `4` untuk model standard). `-s` = skala output; `-s 5` diterima walau `--help` hanya klaim `2,3,4` — diimplementasi sebagai AI 4x + resize ke 5x (`Resizing image according to output scale`). Terverifikasi: 1672x940 → 8360x4700 tepat 5.00x (25/25 file OK).
- Opsi lain: `-r WxH:filter` / `-w width` untuk paksa dimensi, `-g 0|1|auto` pilih GPU, `-t 0` tile auto, `-c 0` tanpa kompresi, `-f jpg|png|webp`.
- GPU di mesin ini: `0` = AMD Radeon integrated, `1` = NVIDIA RTX 3050 Laptop. Default `auto` sudah berhasil; paksa `-g 1` bila butuh kecepatan.

### Batasan MAX_PATH 260 karakter (penting!)

`upscayl-bin.exe` gagal `Couldn't read the image` bila full-path input/output > 260 karakter (umum di folder ini karena nama file panjang, mis. 277 karakter). PowerShell `Copy-Item` tidak punya batasan ini.

Pola batch yang wajib dipakai:
1. `Copy-Item` file asli → nama pendek di `C:\Users\alama\AppData\Local\Temp\opencode\` (mis. `u_in.png`).
2. Jalankan CLI dengan path pendek Temp untuk `-i`/`-o`.
3. `Copy-Item` hasil kembali ke folder tujuan dengan nama asli, hapus file Temp.
4. Untuk banyak file, jalankan loop di background (`shell` dengan `background=true`); tiap file ~1–1.5 menit. Cek `Test-Path` tujuan untuk skip file yang sudah ada.

### Folder kerja terkait

- Source: `gemini_chatgptimage_natal\generated\` — Output 5x: `gemini_chatgptimage_natal\upscaled\` (nama file dipertahankan).

## ExifTool CLI (edit metadata JPG, terverifikasi 2026-10-03)

Binary: `C:\Apps\exiftool\exiftool.exe` (v13.59). `JPEG r/w`.

### Pola triple-sync (wajib untuk Adobe Stock + Dreamstime)

Tulis tiap field ke 3 grup sekaligus agar auto-retrieval kedua agensi terisi:

| Field | Tag exiftool |
|---|---|
| Title | `-XMP-dc:Title`, `-IPTC:ObjectName`, `-XMP-photoshop:Headline` |
| Description | `-XMP-dc:Description`, `-IPTC:Caption-Abstract`, `-EXIF:ImageDescription` |
| Keywords (1 entry per keyword) | `-XMP-dc:Subject`, `-IPTC:Keywords` |
| Copyright | `-XMP-dc:Rights`, `-IPTC:CopyrightNotice`, `-EXIF:Copyright` |
| Creator | `-XMP-dc:Creator`, `-IPTC:By-line`, `-EXIF:Artist` |

Batasan: Adobe Title ideal ≤70 karakter, keywords maks 49 (urutan penting, tanpa merek/duplikat); Dreamstime Title ≤200, keywords ~50, semua English. Dreamstime hanya membaca `Caption-Abstract` (bukan description lain) — file PSD ber-layer harus di-flatten sebelum save JPG.

### Workflow massal (CSV + skrip)

Satu perintah untuk generate+convert+embed sekaligus:

```powershell
.\Process-Batch.ps1 C:\Side\Microstock\<batch>                    # Adobe + Dreamstime
.\Process-Batch.ps1 .\resubmit_dreamstime_261006_0919 -Agency dreamstime -Limit 3
```

Orkestrasi `[1/3]` generate (backend api, otomatis `--no-recursive` bila file di root) → `[2/3]` convert template → `[3/3]` embed ke `<batch>_for_adobe/` + `<batch>_for_dreamstime/`. Berhenti bila diminta (`-Yes` lewati konfirmasi review, `-DryRun` tanpa menulis, `-Limit N` coba kecil dulu).

- Metadata (2 template, `Copyright`/`Creator` = `alamaby`):
  - `gemini_chatgptimage_natal\jpg_metadata_adobe.csv` — Title pendek (Short Title ≤70ch), keywords maks 49 urut penting→umum.
  - `gemini_chatgptimage_natal\jpg_metadata_dreamstime.csv` — Title deskriptif (≤200ch), Description wajib, keywords ~50.
  - Kolom: `SourceFile,Title,Description,Keywords,Copyright,Creator`; Keywords dipisah koma, file UTF8 + quoted.
- Skrip: `Embed-JpgMetadata.ps1` v2 (banner + progress bar ASCII; baca CSV → salin ke folder output → tulis triple-sync 2 fase → verifikasi baca-balik; file sumber tidak diubah). Tanpa argumen = mode interaktif (ditanya folder sumber, CSV, output; DryRun default Ya). Selalu mulai dengan `-DryRun`:
```powershell
.\Embed-JpgMetadata.ps1 -CsvPath .\gemini_chatgptimage_natal\jpg_metadata_adobe.csv -OutDir .\gemini_chatgptimage_natal\for_adobe -DryRun
.\Embed-JpgMetadata.ps1 -CsvPath .\gemini_chatgptimage_natal\jpg_metadata_adobe.csv -OutDir .\gemini_chatgptimage_natal\for_adobe
.\Embed-JpgMetadata.ps1 -CsvPath .\gemini_chatgptimage_natal\jpg_metadata_dreamstime.csv -OutDir .\gemini_chatgptimage_natal\for_dreamstime
```
Upload: isi `for_adobe\` ke Adobe Stock, isi `for_dreamstime\` ke Dreamstime.

### Template metadata per batch

- Satu batch = 2 file: `<batch>_metadata_adobe.csv` + `<batch>_metadata_dreamstime.csv` (contoh: `jpg_metadata_adobe.csv`, `upscaled-1_metadata_adobe.csv`). Kolom sama, `Copyright`/`Creator` default `alamaby`.
- Sumber metadata biasanya 1 file `*_dreamstime_metadata.csv` dengan `SourceFile` berupa nama deskriptif (`001_judul.jpg`). Turunkan jadi 2 template dengan `SourceFile` = **nama file asli**, cocokkan via **nomor 3 digit** (skrip juga bisa auto-match sendiri bila nama tak persis: `OK[auto#NNN]`): pola `__NNN` untuk nama panjang (`...__001-Create-....png` → baris 001), pola `^NNN\.` untuk nama pendek (`007.jpg` → baris 007). Digit sambung 4+ (tanggal `2026-10-03`) dan nama ambigu multi-nomor dilewati (SKIP + warning). Baris tanpa file dilewati (dilaporkan).
- Isi boleh identik bila Title ≤70ch dan keywords ≤49 (lolos kedua agensi); bedakan hanya bila perlu (Adobe: Title pendek; Dreamstime: Title deskriptif ≤200ch).
- **Dreamstime tidak mengenal frasa**: form/fetcher-nya memecah keywords ber-spasi menjadi kata tunggal (`Saudi National Day background` → 4 kata). Template Dreamstime WAJIB kata tunggal lowercase, tanpa stopwords (and/or/the/a/of/no...), maks 70 kata (plafon resmi 80). Template Adobe tetap frasa (mendukung multi-kata).
- Cek keaslian format tiap file via magic bytes sebelum embed (JPEG=`FF D8`, PNG=`89 50 4E 47`) — nama ekstensi saja tidak cukup.
- Folder output per batch: `for_adobe\` + `for_dreamstime\`; bila >1 sumber dalam 1 folder batch, beri prefix sumber (`jpg-1_for_adobe\`). File sumber tidak pernah diubah.

Catatan:
- Baca dulu sebelum tulis: `& "C:\Apps\exiftool\exiftool.exe" -s -G1 -Title -Description -Keywords file.jpg`.
- Skrip bekerja 2 fase per file (reset di invocasi terpisah, lalu tulis bersih) — clear+add se-invocasi menduplikasi list via sinkronisasi IPTC<->XMP. Re-run aman/idempoten. PNG: keywords ditulis via XMP saja (`IPTC:Keywords` dipetakan ke XMP oleh exiftool).
- File dengan ekstensi salah (isi PNG bernama `.jpg`, cpreview magic `89 50 4E 47`) ditolak exiftool (`Not a valid JPG`). Konversi dulu ke JPEG asli (PIL `RGB, quality=95, subsampling=0`) baru embed.
- Di PowerShell, argumen berisi `>`, `<`, `$`, spasi wajib dikutip (`"<TAG><$src"` pakai kutip ganda, `'$...'` pakai kutip tunggal bila ada `$`).
- ExifTool tahan long-path (>260 char), tidak seperti `upscayl-bin.exe`.

## vtracer CLI (JPG kecil -> SVG, terverifikasi 2026-10-07)

Binary: `C:\Apps\vtracer.exe` (v1.0.0-alpha.4). Flag baku yang dipakai `Trace-Svg.ps1`:
`--clustering color-cluster --hierarchical cutout --mode spline`
(petakan eksplisit: tidak ada flag `--compositing`/`--curve-splitting`; `cutout` = nilai `--hierarchical`, `spline` = nilai `--mode`).

Catatan:
- Trace dari JPG KECIL (bukan hasil upscale): vektor di-scale tak terbatas, file kecil = cepat + SVG ramping. Preview besar dibuat terpisah dari SVG (Inkscape, bukan Upscayl).
- Pola batch `Trace-Svg.ps1`: skip bila SVG sudah ada dan valid (berisi `<svg`), tulis atomis via `.tmp`, workaround MAX_PATH via nama pendek di Temp (seperti `Upscale.ps1`).

## Inkscape CLI (SVG -> preview JPG + EPS, terverifikasi 2026-10-07)

Binary: `C:\Program Files\Inkscape\bin\inkscape.com` (1.4.3). Pakai `.com` (bukan `.exe`) untuk batch CLI.

```powershell
& "C:\Program Files\Inkscape\bin\inkscape.com" in.svg --export-type=png --export-width=6000 --export-filename=mid.png
& "C:\Program Files\Inkscape\bin\inkscape.com" in.svg --export-type=eps --export-filename=out.eps
```

Catatan:
- Preview: PNG render Inkscape lalu `ffmpeg -q:v 1` → JPG basename sama (`Export-VectorPreview.ps1`, default lebar 6000px).
- Validasi EPS: file diawali `%!PS` (`25 21 50 53`).
- **ExifTool TIDAK bisa tulis SVG** (`Error: ExifTool does not yet support writing of SVG images`) — metadata SVG di-injeksi sebagai XML native (`<title>`, `<desc>`, paket RDF/XMP di `<metadata>`) oleh `Embed-VectorMetadata.ps1` (best-effort; CSV pendamping tetap sumber kebenaran). **EPS BISA** ditulisi XMP-dc (`Title/Description/Subject/Rights/Creator`, pola 2 fase reset+tulis seperti JPG agar re-run idempoten — terverifikasi baca-balik).
- Orkestrator: `.\Orchestrate-Stock.ps1 -Target SVG|EPS` (tahap 3V metadata → 4V trace → 5V preview → 6V EPS bila EPS → 7V embed paket `for_adobe/` + `for_dreamstime/` berisi pasangan basename-sama + salinan CSV). Paket EPS = `.eps`+`.jpg` saja; paket SVG = `.svg`+`.jpg`. Ganti target di tengah jalan otomatis membersihkan pasangan basi.

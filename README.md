# Microstock — Script Batch

Kumpulan script PowerShell untuk alur kerja microstock (rename, upscale, convert, embed metadata).

## Prasyarat

| Kebutuhan | Dipakai oleh | Default |
|---|---|---|
| `ffmpeg` + `ffprobe` di PATH | `Convert-PngToJpg`, `Convert-WebpToJpg` | — |
| ExifTool | `Embed-JpgMetadata` | `C:\Apps\exiftool\exiftool.exe` |
| Upscayl CLI | `Upscale` | `C:\Program Files\Upscayl\...` |
| vtracer CLI | `Trace-Svg` (jalur SVG/EPS) | `C:\Apps\vtracer.exe` |
| Inkscape CLI | `Export-VectorPreview`, `Convert-SvgToEps` | `C:\Program Files\Inkscape\bin\inkscape.com` |

Bila Windows memblokir eksekusi script:

```powershell
powershell -ExecutionPolicy Bypass -File .\NamaScript.ps1
```

## 1. Rename-Numbered — penomoran file `001_...`

Urutkan file dari paling lama ke paling baru (berdasar `CreationTime`), lalu rename menjadi `001_nama-asli.jpg`, `002_...`, dst. Hanya file langsung di folder (tidak recursive). Re-run aman (prefix `NNN_` lama dikupas dulu, tidak jadi dobel).

```powershell
.\Rename-Numbered.ps1
.\Rename-Numbered.ps1 -Directory "D:\foto" -DryRun
.\Rename-Numbered.ps1 -Directory "D:\foto" -Force
```

| Param | Keterangan |
|---|---|
| `-Directory` | Folder target (ditanya bila kosong) |
| `-DryRun` | Pratinjau saja, tidak mengubah file |
| `-Force` | Lewati konfirmasi (wajib untuk mode non-interaktif) |

Rename berjalan 2 tahap (via nama sementara) agar aman dari tabrakan nama. Mendukung >999 file (otomatis jadi 1000, 1001, ...).

## 2. Convert-WebpToJpg — WEBP ke JPG kualitas maksimal

Konversi semua `*.webp` menjadi `*.jpg` (nama dipertahankan) via `ffmpeg -q:v 1`.

```powershell
.\Convert-WebpToJpg.ps1
.\Convert-WebpToJpg.ps1 -SourceDir .\webp-1 -OutDir .\jpg-1
.\Convert-WebpToJpg.ps1 -SourceDir .\a -OutDir .\b -Quality 2 -Force -Recurse
```

| Param | Keterangan |
|---|---|
| `-SourceDir` / `-OutDir` | Folder sumber / hasil (ditanya bila kosong) |
| `-Quality` | Quantizer mjpeg 1–31, default `1` (terbaik) |
| `-Force` | Timpa/proses ulang file yang sudah ada |
| `-Recurse` | Sertakan subfolder |

Catatan: transparan (alpha) di-flatten ke **putih** (standar microstock), file opaque tidak difilter; WebP animasi hanya diambil frame pertama; metadata EXIF/XMP dipertahankan; output yang sudah ada di-skip.

## 3. Convert-PngToJpg — PNG ke JPG kualitas maksimal

Sama seperti di atas, untuk `*.png` → `*.jpg` via `ffmpeg -q:v 1`.

```powershell
.\Convert-PngToJpg.ps1
.\Convert-PngToJpg.ps1 -SourceDir .\upscaled-1 -OutDir .\jpg-1
.\Convert-PngToJpg.ps1 -SourceDir .\a -OutDir .\b -Quality 2 -Force -Recurse
```

Param sama: `-SourceDir`, `-OutDir`, `-Quality` (1–31, default `1`), `-Force`, `-Recurse`.

## 4. Embed-JpgMetadata — metadata Adobe Stock + Dreamstime

Tulis Title/Description/Keywords/Copyright/Creator dari CSV ke file gambar via ExifTool (triple-sync IPTC+XMP+EXIF agar terbaca kedua agensi). Tanpa argumen = mode interaktif.

```powershell
.\Embed-JpgMetadata.ps1
.\Embed-JpgMetadata.ps1 -CsvPath .\saudi_national_day\jpg-1_metadata_adobe.csv -JpgDir .\saudi_national_day\jpg-1 -OutDir .\saudi_national_day\jpg-1_for_adobe -DryRun
```

| Param | Keterangan |
|---|---|
| `-CsvPath` | CSV Adobe (`Filename,Title,Description,Keywords,Category,Releases,Copyright,Creator`) atau Dreamstime (`SourceFile,...`, tanpa `Category`/`Releases`) — pembaca menerima kedua nama kolom file (`Filename`/`SourceFile`) |
| `-JpgDir` | Folder sumber gambar |
| `-OutDir` | Folder output (default: turunan folder sumber; kosongkan untuk tulis di tempat) |
| `-ExifTool` | Path ExifTool |
| `-DryRun` | Cek + validasi tanpa menulis |
| `-KeepBackup` | Simpan file backup `_original` (default: timpa langsung) |

Selalu mulai dengan `-DryRun`. Pencocokan file cerdas via nomor 3 digit bila nama CSV tidak persis sama. Batas: Title Adobe ideal ≤70 karakter, keywords Adobe maks 49 (frasa), Dreamstime ~80 kata tunggal. Nama file non-ASCII (mis. `…`) tetap diproses normal — peringatan jinak ExifTool `FileName encoding must be specified` disaring otomatis oleh script, tulis metadata tetap terverifikasi baca-balik. Kolom `Category` pada CSV Adobe diisi otomatis dari kategori hasil generator yang dipetakan ke daftar kategori portal resmi (helpx "Choose the right category"); `Other`/tak dikenal dibiarkan kosong agar Sensei mengusulkan sendiri.

## 5. Upscale — upscale via Upscayl CLI

Upscale semua image (`png/jpg/webp`) dalam satu folder memakai model `upscayl-standard-4x`. Melewati file yang sudah ada di output.

```powershell
powershell -ExecutionPolicy Bypass -File Upscale.ps1
.\Upscale.ps1 -InputDir "D:\src" -OutputDir "D:\upscaled" -Scale 5
.\Upscale.ps1 -InputDir "D:\src" -OutputDir "D:\upscaled" -Scale 5 -Force
```

| Param | Keterangan |
|---|---|
| `-InputDir` / `-OutputDir` | Folder sumber / hasil (output dibuat otomatis) |
| `-Scale` | 2–5; wajib diisi eksplisit bila non-interaktif (tanpa `-Scale` hanya bertanya interaktif, Enter = `2`); 4–5 terverifikasi; model selalu `-z 4` |
| `-Model` | Nama model Upscayl (default `upscayl-standard-4x`) |
| `-Force` | Lanjut walau folder output sudah berisi file |

Menangani batas MAX_PATH 260 karakter milik `upscayl-bin.exe` dengan memproses via nama pendek di TEMP. Tiap file ±1–1,5 menit (GPU `auto`; paksa `-g 1` di script bila butuh RTX 3050).

## 6. Orchestrate-Stock — orkestrator AI image sampai siap upload

Satu pintu untuk seluruh alur: rename `001_...` (in-place) → convert JPG kecil → (cabang target) → generate metadata API (dari JPG kecil) → embed ke `for_adobe/` + `for_dreamstime/` + `for_vecteezy_photo/` + `for_pixabay_photo/`. Struktur kerja `_stock/` dibuat di dalam folder input; file sumber asli tidak diduplikasi keluar.

```powershell
.\Orchestrate-Stock.ps1
.\Orchestrate-Stock.ps1 -SourceDir "D:\batch1" -Force
.\Orchestrate-Stock.ps1 -SourceDir "D:\b1","D:\b2","D:\b3" -Force
# Full hands-free (tanpa prompt apa pun):
.\Orchestrate-Stock.ps1 -SourceDir "D:\b1","D:\b2" -Target JPG -Scale 5 -Copyright "alamaby" -Creator "alamaby" -Force
# Jalur vektor (SVG saja, atau EPS+JPG):
.\Orchestrate-Stock.ps1 -SourceDir "D:\v1" -Target SVG -Force
.\Orchestrate-Stock.ps1 -SourceDir "D:\v1" -Target EPS -PreviewWidth 6000 -Force
# Hanya platform tertentu (daftar lengkap di bawah):
.\Orchestrate-Stock.ps1 -SourceDir "D:\batch1" -Target JPG -Platforms Adobe,Dreamstime
.\Orchestrate-Stock.ps1 -SourceDir "D:\batch1" -Target EPS -Platforms Vecteezy -Force
```

| Param | Keterangan |
|---|---|
| `-Target` | `JPG`, `SVG`, atau `EPS`. Tanpa `-Target`: interaktif via menu panah (default `JPG`), non-interaktif otomatis `JPG` |
| `-SourceDir` | Satu atau banyak direktori (`"D:\b1","D:\b2"`); interaktif boleh koma; wajib diisi bila non-interaktif |
| `-Scale` | Skala upscale JPG 2–5, default `5` (jalur JPG saja) |
| `-PreviewWidth` | Lebar render preview JPG vektor 1000–15000px, default `6000` (jalur SVG/EPS) |
| `-Copyright` / `-Creator` | Default `alamaby` |
| `-Platforms` | Subset `Adobe,Dreamstime,Vecteezy,Pixabay`, default semua (= perilaku lama). Hanya platform terpilih yang paketnya ditulis/divalidasi; sisanya dibiarkan utuh. Case-insensitive, duplikat dihapus, `@()` = semua; salah ketik ditolak `ValidateSet` |
| `-Force` | Ulangi paksa tahap hulu (convert/upscale/trace/preview/metadata; menonaktifkan skip/reuse resume). Tidak memengaruhi `-Platforms`. Prompt dihindari dengan mengikat semua param (contoh hands-free), bukan dengan `-Force`; jangan pakai untuk resume |

Cabang target:

- `JPG`: convert JPG kecil → upscale 5x (Upscayl) → JPG final → embed 4 paket (`for_adobe/`, `for_dreamstime/`, `for_vecteezy_photo/`, `for_pixabay_photo/`; JPG triple-sync + salinan CSV Vecteezy/Pixabay).
- `SVG`: trace JPG kecil → SVG (`Trace-Svg`, vtracer color-cluster/cutout/spline) → render preview JPG besar dari SVG (Inkscape + ffmpeg) → embed (`Embed-VectorMetadata`): JPG triple-sync + SVG injeksi `<title>`/`<desc>`/RDF. Paket `for_adobe_svg/` + `for_dreamstime_svg/` + `for_pixabay_svg/` berisi pasangan `.jpg`+`.svg` basename sama + salinan CSV agensi (Vecteezy vektor hanya di jalur EPS).
- `EPS`: sama seperti SVG, ditambah SVG→EPS (Inkscape CLI). Paket `for_adobe_eps/` + `for_dreamstime_eps/` berisi pasangan `.jpg`+`.eps` saja (SVG intermediate tidak dikirim) + `for_vecteezy_eps/` + `for_pixabay_svg/` (ikut terisi di jalur EPS). EPS di-embed XMP-dc via ExifTool.

### Kombinasi `-Platforms` (15 subset × 3 target)

Tanpa `-Platforms` = semua platform (perilaku lama). `-Force` bisa ditempel ke baris mana pun — efeknya hanya pada tahap hulu, bukan pada pemilihan platform.

Matriks folder per target (di dalam `<SourceDir>\_stock\`):

| Target | Adobe | Dreamstime | Vecteezy | Pixabay |
|---|---|---|---|---|
| `JPG` | `for_adobe/` | `for_dreamstime/` | `for_vecteezy_photo/` | `for_pixabay_photo/` |
| `SVG` | `for_adobe_svg/` | `for_dreamstime_svg/` | — (tak didukung) | `for_pixabay_svg/` |
| `EPS` | `for_adobe_eps/` | `for_dreamstime_eps/` | `for_vecteezy_eps/` | `for_pixabay_svg/` |

Folder selalu dibuat saat startup walau platformnya tak dipilih — isinya saja yang tak disentuh (tidak ditulis, tidak dihapus, tidak divalidasi; summary tampil `-`, return object `"-"`).

**Target `JPG`** — kolom Ditulis:

| `-Platforms` | Ditulis |
|---|---|
| *(default)* | `for_adobe`, `for_dreamstime`, `for_vecteezy_photo`, `for_pixabay_photo` |
| `Adobe` | `for_adobe` |
| `Dreamstime` | `for_dreamstime` |
| `Vecteezy` | `for_vecteezy_photo` (+ sanitasi FTP + rewrite CSV paket) |
| `Pixabay` | `for_pixabay_photo` |
| `Adobe,Dreamstime` | `for_adobe`, `for_dreamstime` |
| `Adobe,Vecteezy` | `for_adobe`, `for_vecteezy_photo` |
| `Adobe,Pixabay` | `for_adobe`, `for_pixabay_photo` |
| `Dreamstime,Vecteezy` | `for_dreamstime`, `for_vecteezy_photo` |
| `Dreamstime,Pixabay` | `for_dreamstime`, `for_pixabay_photo` |
| `Vecteezy,Pixabay` | `for_vecteezy_photo`, `for_pixabay_photo` |
| `Adobe,Dreamstime,Vecteezy` | semua kecuali `for_pixabay_photo` |
| `Adobe,Dreamstime,Pixabay` | semua kecuali `for_vecteezy_photo` |
| `Adobe,Vecteezy,Pixabay` | semua kecuali `for_dreamstime` |
| `Dreamstime,Vecteezy,Pixabay` | semua kecuali `for_adobe` |

Validasi JPG (`validation_vecteezy_pixabay.txt`): hanya paket Vecteezy/Pixabay terpilih; bila keduanya tak dipilih → `Validasi skip`, laporan lama dipertahankan.

**Target `SVG`** — Ditulis (setiap subset ber-Vecteezy: warning kuning, Vecteezy di-skip):

| `-Platforms` | Ditulis |
|---|---|
| *(default)* | `for_adobe_svg`, `for_dreamstime_svg`, `for_pixabay_svg` (+ warning Vecteezy) |
| `Adobe` | `for_adobe_svg` |
| `Dreamstime` | `for_dreamstime_svg` |
| `Pixabay` | `for_pixabay_svg` |
| `Vecteezy` | *(nihil — warning, bukan error)* |
| `Adobe,Dreamstime` | `for_adobe_svg`, `for_dreamstime_svg` |
| `Adobe,Pixabay` | `for_adobe_svg`, `for_pixabay_svg` |
| `Dreamstime,Pixabay` | `for_dreamstime_svg`, `for_pixabay_svg` |
| `Adobe,Vecteezy` | `for_adobe_svg` (+ warning) |
| `Dreamstime,Vecteezy` | `for_dreamstime_svg` (+ warning) |
| `Pixabay,Vecteezy` | `for_pixabay_svg` (+ warning) |
| `Adobe,Dreamstime,Pixabay` | ketiga folder non-Vecteezy (tanpa warning) |
| `Adobe,Dreamstime,Vecteezy` | `for_adobe_svg`, `for_dreamstime_svg` (+ warning) |
| `Adobe,Vecteezy,Pixabay` | `for_adobe_svg`, `for_pixabay_svg` (+ warning) |
| `Dreamstime,Vecteezy,Pixabay` | `for_dreamstime_svg`, `for_pixabay_svg` (+ warning) |

Validasi SVG: hanya `for_pixabay_svg` bila Pixabay terpilih.

**Target `EPS`** — Ditulis:

| `-Platforms` | Ditulis |
|---|---|
| *(default)* | `for_adobe_eps`, `for_dreamstime_eps`, `for_vecteezy_eps`, `for_pixabay_svg` |
| `Adobe` | `for_adobe_eps` |
| `Dreamstime` | `for_dreamstime_eps` |
| `Vecteezy` | `for_vecteezy_eps` (+ sanitasi FTP + rewrite CSV paket) |
| `Pixabay` | `for_pixabay_svg` (SVG dari `05_svg`, bukan dari EPS) |
| `Adobe,Dreamstime` | `for_adobe_eps`, `for_dreamstime_eps` |
| `Adobe,Vecteezy` | `for_adobe_eps`, `for_vecteezy_eps` |
| `Adobe,Pixabay` | `for_adobe_eps`, `for_pixabay_svg` |
| `Dreamstime,Vecteezy` | `for_dreamstime_eps`, `for_vecteezy_eps` |
| `Dreamstime,Pixabay` | `for_dreamstime_eps`, `for_pixabay_svg` |
| `Vecteezy,Pixabay` | `for_vecteezy_eps`, `for_pixabay_svg` |
| `Adobe,Dreamstime,Vecteezy` | semua kecuali `for_pixabay_svg` |
| `Adobe,Dreamstime,Pixabay` | semua kecuali `for_vecteezy_eps` |
| `Adobe,Vecteezy,Pixabay` | semua kecuali `for_dreamstime_eps` |
| `Dreamstime,Vecteezy,Pixabay` | semua kecuali `for_adobe_eps` |

Validasi EPS: `for_vecteezy_eps` (bila terpilih) + `for_pixabay_svg` (bila terpilih); keduanya tak dipilih → skip.

Pitfall: tulis `-Platforms Adobe,Dreamstime` (array, tanpa kutip pembungkus) — `-Platforms "Adobe,Dreamstime"` (satu string) ditolak `ValidateSet`.

Catatan: ExifTool tidak mendukung tulis SVG, jadi metadata SVG adalah injeksi XML best-effort (CSV pendamping tetap sumber kebenaran). Uji upload 1 file per agensi dulu sebelum batch besar.

Lanjut dari jalur JPG (resume otomatis): bila satu direktori sudah selesai `-Target JPG` (contoh `witch_halloween\generated-1`), jalankan target vektor pada direktori yang sama **tanpa** `-Force` — tahap yang sudah beres di-skip, hanya yang belum dikerjakan:

```powershell
# Resume SVG (lanjutkan dari JPG yang sudah selesai):
.\Orchestrate-Stock.ps1 -SourceDir "C:\Side\Microstock\witch_halloween\generated-1" -Target SVG -Scale 5 -Copyright "alamaby" -Creator "alamaby"
# Resume EPS:
.\Orchestrate-Stock.ps1 -SourceDir "C:\Side\Microstock\witch_halloween\generated-1" -Target EPS -Scale 5 -Copyright "alamaby" -Creator "alamaby"
```

Penting: **jangan pakai `-Force` untuk resume** — `-Force` artinya ulangi semua dari awal (convert ulang, generate ulang). Tanpa `-Force`: banner `Resume` menampilkan status JPG/SVG/EPS; convert JPG kecil di-skip bila `02_jpg_small` lengkap; metadata di-reuse tanpa API bila 4 CSV embed (Adobe/Dreamstime/Vecteezy/Pixabay) sudah menutupi semua JPG kecil (rebuild tanpa API bila `-Copyright`/`-Creator` berubah; generate API hanya bila ada file baru yang belum termetadata); trace/preview/EPS hanya memproses file yang belum ada (file korup/setengah-jadi otomatis diproses ulang). Paket vektor ditulis ke folder terpisah (`for_adobe_svg/`, `for_dreamstime_svg/`, `for_adobe_eps/`, `for_dreamstime_eps/`) sehingga upload JPG (`for_adobe/`, `for_dreamstime/`) tidak tertimpa.

Antrean >1 direktori jalan berurutan dengan config default + rekap gabungan OK/PARTIAL/GAGAL. Metadata selalu via inference API (`MICROSTOCK_API_KEY` wajib di `.env` generator); backend lokal dinonaktifkan. Run ulang aman: file selesai di-skip, file korup/setengah-jadi otomatis diproses ulang, sisa interupsi rename (`.renametmp` yatim) dipulihkan otomatis.

## Alur kerja umum

Manual per tahap (1→5), atau otomatis sekaligus via `Orchestrate-Stock`:

```
Rename-Numbered → Upscale → Convert-*ToJpg → Embed-JpgMetadata
Orchestrate-Stock (semua tahap JPG sekaligus)
```

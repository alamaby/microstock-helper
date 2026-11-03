# Microstock Helper

Aplikasi otomatisasi alur kerja microstock terpadu berbasis Python (CLI) untuk pemrosesan gambar raster, vektorisasi SVG/EPS, generasi metadata AI via Vision API, serta embedding metadata ke format standar agensi (Adobe Stock, Dreamstime, Vecteezy, Pixabay).

---

## Fitur Utama

- **Startup Preflight Check**: Pemeriksaan dependensi otomatis saat aplikasi dijalankan, mendeteksi ketersediaan seluruh tool CLI eksternal dan konfigurasi API key sebelum pipeline dieksekusi.
- **Pillow Native Processing**: Konversi format raster murni (PNG, WebP, TIF, BMP ke JPEG) tanpa proses eksternal berat, lengkap dengan compositing transparansi (alpha) ke latar belakang putih standar microstock.
- **AI Vision Metadata**: Menghasilkan judul, deskripsi, kata kunci (phrase & single-word), serta kategori resmi agensi menggunakan backend Vision API (Local OpenAI-compatible gateway & Cloudflare Workers AI fallback).
- **Orkestrator End-to-End**: Menjalankan alur lengkap dari penomoran kronologis `001_...`, pembuatan file preview/kecil, inferensi metadata, upscale AI 5x / tracing vektor, hingga pemisahan paket agensi siap upload (`for_adobe`, `for_dreamstime`, `for_vecteezy_*`, `for_pixabay_*`).
- **Bypass Limit MAX_PATH 260 Karakter**: Proteksi cerdas saat menjalankan Upscayl CLI via sandboxing nama pendek di folder `%TEMP%`.
- **Triple-Sync ExifTool**: Injeksi metadata 2 fase (reset + write bersih) ke grup IPTC + XMP + EXIF agar terbaca akurat oleh seluruh portal agensi.

---

## Prasyarat & Tool Eksternal

Aplikasi menggunakan beberapa CLI pihak ketiga yang terpasang di sistem operasi Windows:

| Tool CLI | Fungsi Utama | Jalur Pencarian Default |
|---|---|---|
| **Python** (>= 3.10) | Runtime aplikasi & operasi raster Pillow | PATH sistem |
| **ExifTool** | Embed metadata JPG, PNG, dan PostScript EPS | `C:\Apps\exiftool\exiftool.exe` atau PATH |
| **Upscayl CLI** | AI Image Upscaling (model `upscayl-standard-4x`) | `C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe` |
| **vtracer CLI** | Konversi raster JPG ke SVG vector | `C:\Apps\vtracer.exe` atau PATH |
| **Inkscape CLI** | Render preview JPG 6000px & konversi SVG ke EPS | `C:\Program Files\Inkscape\bin\inkscape.com` atau Chocolatey PATH |
| **ffmpeg / ffprobe** | Utility pendukung video & audio | `C:\ProgramData\chocolatey\bin\ffmpeg.exe` atau PATH |

> Anda dapat mengesampingkan lokasi path binary melalui environment variable jika terpasang di direktori non-standar:
> - `MICROSTOCK_EXIFTOOL_PATH`
> - `MICROSTOCK_UPSCAYL_PATH`
> - `MICROSTOCK_VTRACER_PATH`
> - `MICROSTOCK_INKSCAPE_PATH`
> - `MICROSTOCK_FFMPEG_PATH`
> - `MICROSTOCK_FFPROBE_PATH`

---

## Panduan Instalasi Cepat

### 1. Setup Otomatis

Jalankan script setup 1-klik untuk membuat virtual environment dan menginstal dependensi Python yang dibutuhkan:

```cmd
setup.bat
```

### 2. Konfigurasi API Key

Salin file `.env.example` ke `.env` di root repository (atau di sub-modul) dan isi token API Vision yang digunakan:

```env
MICROSTOCK_API_KEY=kunci_api_vision_anda
MICROSTOCK_API_BASE_URL=http://localhost:8080/v1
MICROSTOCK_API_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
# Opsional: Cloudflare Workers AI Fallback
MICROSTOCK_CF_ACCOUNT_ID=
MICROSTOCK_CF_API_TOKEN=
```

### 3. Diagnosis Kesiapan Sistem (`doctor`)

Periksa apakah seluruh dependency dan binary eksternal telah terdeteksi dengan benar:

```cmd
run.bat doctor
```

Output diagnosis akan menampilkan status Python, modul pendukung, path seluruh binary CLI, serta kesiapan API key.

---

## Penggunaan Perintah CLI

Aplikasi dapat dijalankan melalui launcher `run.bat` di root:

### 1. Jalankan Pipeline Penuh (`run`)

Menjalankan orkestrator end-to-end dari raw images hingga paket agensi siap upload:

```cmd
# Jalur Foto / Raster (JPG)
run.bat run "D:\Karya\Batch_01" --target JPG --scale 5

# Jalur Vektor SVG (Adobe, Dreamstime, Pixabay)
run.bat run "D:\Karya\Batch_Vektor" --target SVG

# Jalur Vektor EPS + Preview JPG (Adobe, Dreamstime, Vecteezy, Pixabay)
run.bat run "D:\Karya\Batch_Vektor" --target EPS --preview-width 6000

# Hanya untuk platform tertentu:
run.bat run "D:\Karya\Batch_01" --target JPG --platforms Adobe,Dreamstime
```

### 2. Batch Processing Metadata & Embed (`batch`)

Menjalankan alur 3 langkah standar: generate metadata AI -> convert CSV template -> embed ke folder output agensi:

```cmd
run.bat batch "D:\Karya\Batch_01" --agencies both
run.bat batch "D:\Karya\Batch_01" --agencies adobe --limit 5 --dry-run
```

### 3. Konversi Raster ke JPG (`convert`)

Mengonversi PNG/WebP/BMP ke format JPEG kualitas tinggi dengan alpha compositing latar belakang putih:

```cmd
run.bat convert "D:\Karya\RawPNG" --out "D:\Karya\JPG" --quality 95
# Downsampling sisi terpanjang ke 1000px (untuk keperluan preview / small)
run.bat convert "D:\Karya\RawPNG" --out "D:\Karya\JPG_Small" --max-edge 1000
```

### 4. Penomoran Kronologis (`renumber`)

Mengurutkan file media berdasarkan tanggal pembuatan file lalu memberikan awalan urut `001_...`:

```cmd
# Cek pratinjau rencana rename
run.bat renumber "D:\Karya\Batch_01" --dry-run

# Eksekusi rename
run.bat renumber "D:\Karya\Batch_01"
```

### 5. Upscale Gambar (`upscale`)

Melakukan upscaling gambar secara batch via Upscayl CLI:

```cmd
run.bat upscale "D:\Karya\JPG_Small" --out "D:\Karya\Upscaled" --scale 5
```

### 6. Tracing Vektor SVG (`trace`)

Melakukan tracing kurva spline otomatis via vtracer CLI:

```cmd
run.bat trace "D:\Karya\JPG_Small" --out "D:\Karya\SVG"
```

### 7. Render Preview Vektor (`vector-preview`)

Merender SVG menjadi file gambar JPG beresolusi tinggi (default 6000px):

```cmd
run.bat vector-preview "D:\Karya\SVG" --out "D:\Karya\Previews" --width 6000
```

### 8. Konversi SVG ke EPS (`convert-eps`)

Mengonversi file SVG ke format PostScript EPS via Inkscape CLI:

```cmd
run.bat convert-eps "D:\Karya\SVG" --out "D:\Karya\EPS"
```

### 9. Embed Metadata JPG/PNG (`embed-jpg`)

Menyuntikkan judul, deskripsi, dan kata kunci dari file CSV ke file gambar via ExifTool:

```cmd
run.bat embed-jpg --csv "D:\Karya\metadata.csv" --images "D:\Karya\JPG" --out "D:\Karya\for_adobe"
```

### 10. Embed Metadata Paket Vektor (`embed-vector`)

Menyuntikkan metadata ke pasangan file vektor (SVG/EPS) dan preview JPG pendamping:

```cmd
run.bat embed-vector --csv "D:\Karya\metadata.csv" --jpg-dir "D:\Karya\Previews" --vec-dir "D:\Karya\EPS" --out "D:\Karya\for_adobe_eps"
```

---

## Struktur Output Direktori

Saat pipeline `run` dieksekusi, struktur folder kerja terisolasi dibuat di dalam direktori target:

```text
<SourceDir>/
├── 001_gambar.png                  # File asli (nama diurutkan chronologically)
└── _stock/                         # Folder kerja & hasil akhir
    ├── 01_raw/                     # Arsip file sumber
    ├── 02_jpg_small/               # JPG resolusi rendah untuk inferensi AI & tracing
    ├── 03_metadata/                # Master CSV & 4 template agensi terpisah
    ├── 04_upscaled/                # Hasil upscale AI (jalur JPG)
    ├── 05_final_jpg/               # JPG final resolusi maksimum
    ├── 05_svg/                     # File vektor SVG (jalur SVG/EPS)
    ├── 05_preview_jpg/             # Preview render 6000px
    ├── 06_eps/                     # PostScript EPS (jalur EPS)
    ├── for_adobe/                  # Paket final siap upload Adobe Stock
    ├── for_dreamstime/             # Paket final siap upload Dreamstime
    ├── for_vecteezy_photo/         # Paket foto ter-sanitasi FTP untuk Vecteezy
    └── for_pixabay_photo/          # Paket foto siap upload Pixabay
```

---

## Menjalankan Unit Tests

Untuk memverifikasi fungsionalitas dan integritas seluruh modul:

```cmd
.\microstock-metadata-generator\.venv\Scripts\pytest.exe -v tests
```

---

## Kompatibilitas Script PowerShell Legacy

Script PowerShell legacy (`Orchestrate-Stock.ps1`, `Process-Batch.ps1`, `Embed-JpgMetadata.ps1`, dll.) tetap dipertahankan di repository ini untuk kompatibilitas alur kerja yang sudah ada sebelumnya.

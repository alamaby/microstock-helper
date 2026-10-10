# Vecteezy + Pixabay Upload Directories Implementation

- **Date**: 2026-10-10 22:48:00 +07:00
- **Task / Problem**: Menambah direktori siap-upload Vecteezy dan Pixabay ke `Orchestrate-Stock.ps1` untuk scope JPG, SVG, EPS dengan CSV Vecteezy (`License=free`), CSV pendamping Pixabay, sanitasi nama file Vecteezy (tanpa spasi), dan laporan kesiapan upload warn-only sesuai [plans/2026-10-10-vecteezy-pixabay-upload-directories.md](file:///C:/Side/Microstock/plans/2026-10-10-vecteezy-pixabay-upload-directories.md).
- **Plan Link**: [plans/2026-10-10-vecteezy-pixabay-upload-directories.md](file:///C:/Side/Microstock/plans/2026-10-10-vecteezy-pixabay-upload-directories.md)

## Berkas yang Diubah / Ditambah

- [`Orchestrate-Stock.ps1`](file:///C:/Side/Microstock/Orchestrate-Stock.ps1):
  - Signature dan transformasi `ConvertTo-EmbedCsvs` untuk meng-emit 4 CSV sekaligus (Adobe, Dreamstime, Vecteezy, Pixabay) dengan capping kata kunci Vecteezy 30 frasa dan Pixabay 25 kata tunggal, serta `License="free"` untuk Vecteezy.
  - Wire call-sites TAHAP 5 & 3V dengan logic reuse 3-tier (12 syarat pada Tier 1).
  - Penambahan 4 direktori upload: `for_vecteezy_photo`, `for_pixabay_photo`, `for_vecteezy_eps`, `for_pixabay_svg`.
  - Packaging TAHAP 6 (JPG) dan TAHAP 7V (vektor) dengan guard per-Target (`SVG` vs `EPS`).
  - Helper sanitasi `Get-SafeUploadName` dan `Repair-VecteezyPackage` (deterministik in-place, rename 2-tahap anti-tabrakan, rewrite salinan CSV paket extensionless).
  - Helper validasi `Test-UploadReadiness` (cek integritas V1, dimensi MP proksi V2, batas ukuran 1-50MB V3, profil sRGB V4, konsistensi CSV V6, checklist manual V7) menghasilkan laporan warn-only `validation_vecteezy_pixabay.txt`.
  - Pelaporan summary upload directories baru dan penambahan properti `Vecteezy` & `Pixabay` pada return object.
- [`plans/2026-10-10-vecteezy-pixabay-upload-directories.md`](file:///C:/Side/Microstock/plans/2026-10-10-vecteezy-pixabay-upload-directories.md): Update task checklist S1–S8 dan Progress Log.

## Keputusan Teknis & Bisnis

- Kolom `License` CSV Vecteezy dikunci literal `"free"` tanpa parameter baru.
- Scope mendukung JPG (photo), EPS (Vecteezy vector), dan SVG (Pixabay vector).
- Direktori kind-pure: `for_vecteezy_photo`, `for_pixabay_photo`, `for_vecteezy_eps`, `for_pixabay_svg`.
- Sanitasi nama file (tanpa spasi / karakter non-alphanumeric selain strip dan underscore) hanya berlaku untuk paket Vecteezy; file sumber, paket Adobe/Dream/Pixabay, dan CSV induk tetap tidak diubah.
- Validasi upload bersifat **warn-only** (tidak pernah menghentikan pipeline atau melempar fatal error).

## Asumsi & Risiko

- Vektor Vecteezy memerlukan format EPS (pada run `Target=SVG`, paket Vecteezy dilewati dengan pesan informatif dan operator diarahkan menggunakan `Target=EPS`).
- Proksi dimensi MP untuk vektor dihitung dari preview JPG pendamping.
- Script Embed yang ada (`Embed-JpgMetadata.ps1` dan `Embed-VectorMetadata.ps1`) dipertahankan tanpa modifikasi.

## Blocker / Open Items

- Tidak ada blocker teknis aktif.
- Unggah ke Pixabay tetap memerlukan centang manual `AI-generated` dan pengisian tag melalui antarmuka web Pixabay.

## Verifikasi yang Dilakukan

1. PowerShell Syntax Parser: 0 error pada `Orchestrate-Stock.ps1`.
2. Verifikasi fungsi transformasi CSV: pembentukan 4 CSV, perbandingan regresi Adobe/Dream byte-identik, capping keywords/titles, dan kolom `License=free`.
3. Verifikasi sanitasi dan rewrite CSV paket: deteksi tabrakan, rename deterministik, kesesuaian 1:1 antara nama file di disk dan kolom Filename CSV (diff count = 0), dan idempotensi rerun.
4. Verifikasi end-to-end fixture EPS (`Target=EPS`): tahapan trace, render preview, convert EPS, embed paket, sanitasi, dan pembuatan laporan `validation_vecteezy_pixabay.txt` berjalan sukses dengan `ExitCode: 0`.

## Proposed Conventional Commit (1 baris)

```text
feat(orchestrator): add Vecteezy and Pixabay upload directories and packaging
```

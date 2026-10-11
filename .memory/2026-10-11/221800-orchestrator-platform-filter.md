# Orchestrator Platform Filter (`-Platforms`)

- **Tanggal / Waktu**: 2026-10-11 22:18:00 +07:00
- **Topik**: Penambahan opsi platform filter `-Platforms` pada `Orchestrate-Stock.ps1`
- **Plan Terkait**: [plans/2026-10-11-orchestrator-platform-filter-plan.md](file:///C:/Side/Microstock/plans/2026-10-11-orchestrator-platform-filter-plan.md)

## Task & Masalah
Sebelumnya, `Orchestrate-Stock.ps1` selalu meng-embed dan memvalidasi ke seluruh 4 platform mikrostock (Adobe, Dreamstime, Vecteezy, Pixabay) sesuai target format. User membutuhkan opsi untuk memilih subset platform yang akan dibuat atau dibuat ulang (misalnya hanya platform tertentu yang ditolak atau perlu di-rebuild) tanpa menyentuh atau menghapus paket upload platform lainnya.

## Berkas yang Diubah
- [Orchestrate-Stock.ps1](file:///C:/Side/Microstock/Orchestrate-Stock.ps1) — Blok `param` (tambah `-Platforms`), helper `Test-PlatformSelected`, normalisasi dan prompt interaktif di `Main`, gating TAHAP 6 (JPG), gating TAHAP 7V (vektor), ringkasan/return object di `finally`, serta dokumentasi `.DESCRIPTION` dan `.EXAMPLE`.
- [plans/2026-10-11-orchestrator-platform-filter-plan.md](file:///C:/Side/Microstock/plans/2026-10-11-orchestrator-platform-filter-plan.md) — Centang seluruh tasks S1–S6, update checklist dan Progress Log.

## Keputusan Teknis
1. **Backward Compatibility**: Default parameter `-Platforms` bernilai `@("Adobe", "Dreamstime", "Vecteezy", "Pixabay")` dengan `ValidateSet`, sehingga pemanggilan tanpa argumen tetap berperilaku identik seperti sebelumnya.
2. **Isolasi Seleksi**: Menggunakan helper tunggal `Test-PlatformSelected` berbasis perbandingan case-insensitive terhadap koleksi `$Platforms`.
3. **Overwrite Semantics**: Child script `Embed-JpgMetadata.ps1` dan `Embed-VectorMetadata.ps1` memakai `Copy-Item -Force`, sehingga platform yang dipilih otomatis di-overwrite bersih, sementara platform yang tidak dipilih tidak disentuh sama sekali (tidak ditulis ulang dan tidak dihapus).
4. **Gating Validasi Portal**: `Test-UploadReadiness` hanya dieksekusi jika platform subset Vecteezy atau Pixabay terpilih. Jika tidak terpilih, validasi di-skip agar tidak menimpa laporan `validation_vecteezy_pixabay.txt` sebelumnya.
5. **Penanganan Kasus Tak Didukung (Vecteezy + SVG)**: Jika `Target=SVG` dan `Platforms` memuat Vecteezy, orkestrator tidak throw/fatal melainkan mencetak warning kuning informatif dan melaporkan `(n/a - butuh Target=EPS)` pada summary.
6. **Summary & Return Object Akurat**: Platform yang tidak dipilih ditampilkan sebagai `(skip - tak dipilih)` pada stdout summary dan bernilai `"-"` pada properti return object.

## Verifikasi yang Dilakukan
- PowerShell AST Parser: `errors=0`.
- Inspeksi parameter: `Parameters['Platforms'].ParameterType.Name` bernilai `String[]`.
- Dot-source test: `Test-PlatformSelected` case-insensitive dan mendeteksi subset dengan benar.
- Matriks pengujian manual pada fixture sementara (`C:\Users\alama\AppData\Local\Temp\opencode\platfix`):
  1. `JPG-Adobe-saja`: lolos (hanya `for_adobe` yang terisi, `Adobe=1, Dreamstime=-, Vecteezy=-, Pixabay=-`).
  2. `JPG-default-semua`: lolos (keempat platform di-embed dan divalidasi).
  3. `EPS-Vecteezy-saja`: lolos (`for_vecteezy_eps` terisi dan disanitasi, platform lain diskip).
  4. `SVG-Vecteezy-saja`: lolos (warning informatif, tidak ada error fatal, summary `(n/a - butuh Target=EPS)`).
  5. `SVG-default`: lolos (Adobe, Dreamstime, Pixabay terisi; Vecteezy diberi warning SVG).
  6. `Pixabay-saja`: lolos (`for_pixabay_photo` terisi, platform lain diskip).

## Proposed Conventional Commit
`feat(orchestrator): add -Platforms filter option for selective package generation`

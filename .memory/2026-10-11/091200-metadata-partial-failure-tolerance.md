# Metadata Partial-Failure Tolerance (Tahap 5 JPG & Tahap 3V)

- **Timestamp**: 2026-10-11 09:12:00 +07:00
- **Plan File**: [plans/2026-10-11-metadata-partial-failure-plan.md](file:///C:/Side/Microstock/plans/2026-10-11-metadata-partial-failure-plan.md)

## Task / Masalah
Pada kasus nyata batch `natal_261006_1543`, 96 file berhasil di-generate metadatanya tetapi 1 file gagal (`Empty model response` dari model API). Kegagalan 1 file ini menyebabkan generator mengembalikan `exit 1` (`EXIT_ITEM_FAILURE`), yang sebelumnya langsung memicu `throw` fatal di `Orchestrate-Stock.ps1` Tahap 5 JPG dan Tahap 3V Tier-3. Akibatnya, seluruh 96 file sukses terbuang dan folder upload (`for_adobe`, `for_dreamstime`, `for_vecteezy_photo`, `for_pixabay_photo`) kosong meski proses AI memakan waktu lebih dari 4 jam.

## Berkas yang Diubah
- [`Orchestrate-Stock.ps1`](file:///C:/Side/Microstock/Orchestrate-Stock.ps1):
  - Tahap 5 JPG: Menangkap `$genExit`, menghitung baris `success`/`skipped` di `metadata.csv`. Hanya `exit 1` dengan `genOkRows > 0` yang ditoleransi sebagai status `PARTIAL`, mencatat daftar gagal ke `failed_05_metadata.txt`, dan melanjutkan pipeline ke `ConvertTo-EmbedCsvs` serta `Embed-JpgMetadata.ps1`. Kode exit fatal (`2/3/4`) atau exit 1 tanpa ada baris sukses tetap memicu `throw`.
  - Tahap 3V Tier-3: Menerapkan paritas toleransi partial failure yang sama untuk vektor (SVG/EPS), mencatat daftar gagal ke `failed_03_metadata.txt`.

## Keputusan Teknis & Bisnis
1. **Tidak Mengubah Kontrak Generator Python**: Kontrak generator di `constants.py` dan `cli.py` tetap utuh (`EXIT_ITEM_FAILURE=1` jika ada item gagal).
2. **Pembedaan Exit Code**: Hanya `exit 1` yang ditoleransi bila ada baris sukses (`OK > 0`); `exit 2` (config), `exit 3` (model load), dan `exit 4` (output error) tetap fatal.
3. **Pembersihan Bersih File Gagal**: Menggunakan `Remove-Item -Force` sebelum memanggil `Write-FailedList` agar rerun tidak meninggalkan item basi tanpa perlu mengubah helper global.
4. **Offline Recovery Safe**: Menguji verifikasi pemulihan data nyata pada direktori temporary tanpa menyentuh data produksi atau memicu biaya API ulang.

## Asumsi & Risiko
- **Risiko**: Kegagalan sistemik prompt pada 1 file akan terulang saat operator melakukan rerun.
- **Mitigasi**: Log `failed_items.json` membuktikan kegagalan disebabkan transient `InvalidModelResponseError` (respons kosong dari penyedia model). Status `PARTIAL` memberi visibilitas jelas di ringkasan terminal dan file `failed_05_metadata.txt`.

## Blocker / Open Items
- Tidak ada blocker kode. Pemulihan ke folder produksi `_stock/for_*` dapat dilakukan operator via normal rerun checkpoint tanpa `-Force`.

## Verifikasi yang Dilakukan
- Baseline verification S0 membaca file nyata `natal_261006_1543` (97 final jpg, 0 for_adobe, log FATAL exit 1).
- Pengecekan sintaks PowerShell `Parser::ParseFile` pada `Orchestrate-Stock.ps1` menghasilkan `PARSE-OK`.
- Unit test pytest `tests/test_cli.py` pada modul metadata generator lulus 100% (11 passed).
- Pengujian deterministik fixture S4 membuktikan logika guard menoleransi `exit 1` (dengan baris sukses) dan memicu `throw` pada `exit 2` atau `exit 1` dengan 0 baris sukses.
- Pengujian pemulihan S5 pada data nyata `natal_261006_1543` sukses menghasilkan 4 CSV embed dengan masing-masing 96 baris dan 96 file JPG ter-embed di direktori temporary tanpa panggil API.

## Proposed Commit Message
`fix(orchestrator): tolerate metadata partial failure exit 1 in stage 5 and 3v`

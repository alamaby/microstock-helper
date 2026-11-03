# Diagnosis: 9Router Stripping Image Payload on Cloudflare Vision Model

- **Timestamp**: 2026-11-03 15:10:00 +07:00
- **Status**: Completed
- **Topic**: Investigasi penyebab hasil metadata Winter Microstock halusinasi / tidak sesuai gambar

## Masalah / Problem
Pada folder `Winter Microstock/for_adobe` dan `Winter Microstock/output-api`, seluruh file (contoh: stiker musim dingin, kendaraan salju, hewan musim dingin) menghasilkan metadata yang tidak sesuai gambar (hallucinated slop):
- Judul: `"Person holding smartphone in front of cityscape"` atau `"Person holding smartphone in modern office"`.
- Kategori: `"People"`.
- Keywords: `"person, smartphone, office, desk, laptop, papers, modern, business, technology..."`.

## Temuan Verifikasi & Analisis Akar Masalah (Root Causes)

1. **Rute Eksekusi**:
   - `microstock` dijalankan menggunakan default gateway `http://127.0.0.1:20128/v1` dengan model `combo-3` via environment `MICROSTOCK_API_MODEL=combo-3`.
   - Port 20128 dikelola oleh **9Router** (`C:\Users\alama\AppData\Roaming\npm\node_modules\9router`).
   - Di database 9Router (`%APPDATA%\9router\db\data.sqlite`), model combo `combo-3` dipetakan ke `cf/@cf/meta/llama-4-scout-17b-16e-instruct` (provider `cloudflare-ai`).

2. **Akar Masalah Utama: 9Router Menghapus Konten Gambar (`flattenContent: true`)**:
   - Pada internal bundle 9Router (`chunk 7373.js`), provider `cloudflare-ai` memiliki rule:
     ```javascript
     { provider: "cloudflare-ai", flattenContent: true }
     ```
   - Logika transformasinya:
     ```javascript
     if (g.flattenContent && Array.isArray(c.messages)) {
       for (let a of c.messages) {
         if (a && Array.isArray(a.content)) {
           a.content = a.content
             .map(a => a?.type === "text" && typeof a.text === "string" ? a.text : "")
             .join("");
         }
       }
     }
     ```
   - Rule ini mengasumsikan Cloudflare AI tidak mendukung format array content multimodal, sehingga seluruh blok non-teks (`image_url` base64 data URI) **dihapus total** sebelum request diteruskan ke Cloudflare.

3. **Akibat pada Model LLM (Llama 4 Scout)**:
   - Model `@cf/meta/llama-4-scout-17b-16e-instruct` hanya menerima teks prompt murni tanpa data visual sama sekali (terverifikasi: `prompt_tokens` hanya ~439–873 token, bukan ~2.5k–3k token).
   - Karena prompt `MICROSTOCK_V3` mewajibkan output JSON metadata stock foto dan melarang placeholder generik dengan `temperature: 0.0`, model terpaksa menghalusinasikan deskripsi stok foto generik paling populer ("Person holding smartphone in modern office").

4. **Uji Komparasi Terverifikasi**:
   - **Via 9Router `combo-3`**: Model membalas `"No image provided. Describe or share image."` atau menghalusinasikan `"Person holding smartphone..."`.
   - **Langsung ke Cloudflare Workers AI Endpoint** (`https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions`):
     - Prompt tokens: 2923.
     - Model menghasilkan metadata akurat 100%:
       `"title": "Felt stickers of winter vehicles and animals"`, `"category": "Transportation"`, keywords: `"snowmobile", "sled", "dogs", "truck", "horse", "sleigh", "winter vehicles", "felt stickers"`.

## Rekomendasi Solusi
1. **Bypass 9Router untuk Vision Task**:
   - Arahkan generator metadata langsung ke endpoint Cloudflare Workers AI tanpa melalui proxy 9Router port 20128.
   - Konfigurasi model di `.env`: `MICROSTOCK_CF_MODEL=@cf/meta/llama-4-scout-17b-16e-instruct`.
2. **Re-generate & Re-embed Metadata**:
   - Jalankan ulang `microstock generate` langsung ke provider Cloudflare untuk batch `Winter Microstock`.
   - Tulis ulang metadata pada file `Winter Microstock/for_adobe`.

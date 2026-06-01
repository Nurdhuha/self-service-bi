# Prosedur Pengujian (Testing Procedure): SQL Llama BI System

Dokumen ini mendefinisikan langkah-langkah sistematis untuk menguji, menganalisis, dan meningkatkan akurasi penerjemahan alami bahasa Indonesia ke PostgreSQL (Text-to-SQL) pada data E-commerce Olist.

---

## 🚀 Tahap 1: Persiapan Environment & Menjalankan Server

1. **Jalankan PostgreSQL**: Pastikan database PostgreSQL di Windows aktif dan menerima koneksi dari WSL.
2. **Aktifkan Server Backend**: Buka terminal WSL baru, aktifkan environment Anda, lalu jalankan backend:
   ```bash
   cd "/mnt/d/Stupen/Proyek Studi Independen/src/backend"
   python3 app.py
   ```
   *Tunggu hingga terminal menampilkan:*  
   `✅ SQL Llama model successfully loaded and ready for inference!`

---

## 🤖 Tahap 2: Menjalankan Automated Integration Testing (15 Skenario)

Kami telah mendesain dan memperluas skrip pengujian otomatis Anda menjadi **15 kasus uji (test cases)** yang mencakup berbagai variasi kompleksitas bisnis intelijen (BI).

Untuk menjalankan pengujian otomatis:
1. Buka **tab terminal WSL kedua** (jangan matikan server backend di tab pertama).
2. Jalankan perintah berikut:
   ```bash
   cd "/mnt/d/Stupen/Proyek Studi Independen/src/backend"
   python3 test_integration.py
   ```

---

## 📊 Tahap 3: Membaca & Menganalisis Laporan Hasil Uji (Responses JSON)

Setiap kali pengujian selesai dijalankan, rangkuman detail akan secara otomatis disimpan sebagai file JSON terstruktur dengan timestamp di dalam folder `responses/`:
`responses/test_run_summary_YYYYMMDD_HHMMSS.json`

### Cara Menganalisis Log Uji:
1. **Passed (Status: "passed")**: AI berhasil membuat SQL query yang valid dan mengeksekusinya ke database dengan mengembalikan record data.
2. **Failed (Status: "failed")**: Terjadi kegagalan. Cek bagian `"error_detail"` di dalam file JSON untuk mengetahui penyebabnya:
   * **Syntax Error**: Penulisan SQL ada yang keliru (misal: tanda petik `'` tidak tertutup).
   * **Column Mismatch**: AI memanggil nama kolom yang tidak ada pada tabel fisik database (misal: memanggil `product_name_length` padahal tidak tersedia).
   * **Join Hallucination**: AI mencoba menggabungkan tabel menggunakan kolom yang salah (misal: menggabungkan `sellers` dan `order_items` pada `product_id`).

---

## 🔄 Tahap 4: Siklus Perbaikan & Tuning (The Feedback Loop)

Jika Anda menemukan kasus uji yang gagal (failed), ikuti langkah perbaikan berikut tanpa perlu melatih ulang (retrain) model:

1. **Analisis Schema Context**: Pastikan kolom yang memicu error telah dihapus atau diperbaiki di dalam `OLIST_SCHEMA_CONTEXT` dan helper `prune_schema_context` di [src/backend/app.py](file:///D:/Stupen/Proyek%20Studi%20Independen/src/backend/app.py).
2. **Tweak Few-Shot Examples**: Jika model bingung dalam menyusun struktur `JOIN` atau `GROUP BY` pada skenario tertentu, tambahkan atau ganti salah satu dari 3 contoh di `ALPACA_PROMPT_TEMPLATE` dengan format query yang benar.
3. **Restart & Re-test**:
   * Hentikan server backend (`Ctrl + C`).
   * Jalankan ulang backend (`python3 app.py`).
   * Jalankan ulang skrip pengujian (`python3 test_integration.py`).

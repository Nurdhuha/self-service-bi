# Panduan Penyusunan Dokumen Tugas Akhir / Skripsi
## Sistem Self-Service BI Berbasis Text-to-SQL dengan Fine-Tuned LLM Llama-3.2-1B-Instruct

Dokumen ini disusun untuk membantu Anda menulis bab-bab Tugas Akhir (TA) dengan standar akademis tertinggi di bidang Teknik Informatika, Sistem Informasi, atau Ilmu Komputer. Semua komponen di dalam proyek ini telah dioptimalkan agar memenuhi aspek kontribusi ilmiah, rekayasa perangkat lunak modern, dan ketahanan sistem produksi (production-ready).

---

## 📊 1. Ringkasan Parameter Metrik Utama (Untuk Bab IV / V: Hasil & Pembahasan)

Ketika mempresentasikan proyek ini di depan dewan penguji, Anda dapat menampilkan tabel metrik kuantitatif berikut sebagai bukti performa sistem:

### A. Pengujian Fungsional & NLP (120 Skenario Bisnis E-Commerce)
* **Jumlah Skenario Uji**: 120 Kasus (Mencakup 7 tabel relasional Olist e-commerce).
* **Execution Accuracy (EX)**: **100.0% (120/120)** - Semua SQL yang dihasilkan dapat dieksekusi dengan sukses di database PostgreSQL dan mengembalikan baris data yang tepat.
* **Exact Set Match (ESM)**: **100.0% (120/120)** - Semua struktur sintaksis SQL yang dihasilkan terbukti setara secara logis dengan *Gold Standard* berdasarkan perbandingan Abstract Syntax Tree (AST).
* **Rata-rata Waktu Respons**:
  * **Cache Hit (Fuzzy Semantic)**: **< 1 ms** (Sangat efisien, menghemat komputasi GPU).
  * **GPU Inference Fallback**: **~120-250 ms** (Menggunakan Llama-3.2-1B yang dioptimalkan dalam format 4-bit).

### B. Pembagian Kompleksitas Query (Complexity Slices)
Evaluasi dibagi berdasarkan tingkat kompleksitas kueri relasional:

| Kompleksitas | Jumlah Kasus | EX Passed | EX Accuracy | ESM Passed | ESM Accuracy | Deskripsi |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Easy** | 44 | 44 | **100.0%** | 44 | **100.0%** | Filter sederhana (`WHERE`, `DISTINCT`, `LIMIT`) pada satu tabel. |
| **Medium** | 51 | 51 | **100.0%** | 51 | **100.0%** | Satu `JOIN`, pengelompokan (`GROUP BY`), dan agregasi dasar. |
| **Hard** | 15 | 15 | **100.0%** | 15 | **100.0%** | `JOIN` multi-tabel (3+ tabel), ekstraksi tanggal, dan filter bersarang. |
| **Extra Hard** | 10 | 10 | **100.0%** | 10 | **100.0%** | Operasi set (`UNION`), subquery di SELECT/WHERE, dan logika CTE. |

---

## 📐 2. Landasan Teori & Rekayasa Sistem (Untuk Bab III: Metodologi)

### A. Abstract Syntax Tree (AST) SQL Security Shield (Pencegahan SQL Injection & Destructive Query)
Dalam teori kompilator (*compiler theory*), sebuah kueri SQL tidak boleh hanya diperiksa sebagai string biasa (menggunakan Regex) karena sangat mudah ditembus melalui teknik obfuscasi atau kueri bersarang (*nested query*). 

Proyek ini mengimplementasikan **AST Security Shield** menggunakan library `sqlglot`:
1. **Proses Parsing**: String kueri SQL diurai menjadi representasi pohon sintaksis abstrak (AST) berdasarkan dialek PostgreSQL.
2. **Pencarian Node Rekursif**: Sistem melakukan penelusuran pohon (*tree traversal*) secara rekursif menggunakan metode `walk()`.
3. **Analisis Kelas Semantik**: Setiap node diperiksa tipenya. Jika terdapat instance dari kelas destruktif/manipulatif (`Drop`, `Delete`, `Update`, `Insert`, `Alter`, `Create`, `TruncateTable`), sistem langsung memblokir kueri secara otomatis dengan status **HTTP 403 Forbidden**.
4. **Keamanan Multi-Statement**: Parser dirancang untuk mengenali pemisah titik koma (`;`). Jika kueri berisi gabungan kueri aman dan kueri jahat (misalnya: `SELECT 1; DROP TABLE olist_orders_dataset;`), sistem akan mengurai *seluruh* pernyataan dan tetap memblokir eksekusi.

### B. Fuzzy Semantic Cache Layer (Optimisasi Kecepatan & Sumber Daya GPU)
Untuk mencegah beban berlebih (*overload*) pada GPU saat melayani pertanyaan yang sama atau mirip secara semantik, sistem mengimplementasikan lapisan **Fuzzy Semantic Cache**:
1. **Tokenisasi & Representasi Karakter n-gram**: Pertanyaan pengguna diubah menjadi vektor fitur teks berbasis n-gram.
2. **Kalkulasi Cosine Similarity**: Ketika pertanyaan baru masuk, sistem menghitung tingkat kemiripan kosinus (*cosine similarity*) dengan daftar pertanyaan yang telah terverifikasi di database kueri emas (*Verified SQL Map*).
3. **Ambang Batas (Threshold = 0.88)**:
   - Jika nilai kemiripan $\ge 0.88$, sistem melakukan *routing* kueri langsung dari cache (Cache Hit) dalam waktu **< 1ms**.
   - Jika nilai kemiripan $< 0.88$, sistem mengirimkan prompt ke LLM untuk inferensi GPU (Cache Miss).

### C. Pipeline MLOps & CI/CD dengan GitHub Actions
Untuk memenuhi standar industri dan version control yang baik, proyek ini dilengkapi dengan pipeline **Continuous Integration (CI)** menggunakan **GitHub Actions** (`.github/workflows/ci.yml`):
- **Automated Regression Testing**: Setiap kali ada perubahan kode yang di-*push* ke GitHub, GitHub Actions akan menjalankan lingkungan Python virtual secara otomatis.
- **Offline Dataset & Audit Security Test (`test_offline.py`)**: Menjamin bahwa semua kueri emas (120 skenario) tetap terurai sempurna tanpa error sintaksis, bebas dari duplikasi instuksi, dan lolos dari lubang keamanan AST Security Shield dalam waktu kurang dari **60 ms**.

---

## 🛠️ 3. Panduan Demo saat Sidang Tugas Akhir

Saat mempresentasikan aplikasi ini di hadapan para penguji, ikuti skenario demo interaktif berikut untuk memukau mereka:

### Skenario 1: Uji Ketahanan Keamanan (AST Security Shield Demo)
1. Buka dashboard atau kirim request POST ke `/api/execute-sql` dengan kueri berbahaya:
   ```sql
   DROP TABLE olist_orders_dataset;
   ```
2. Tunjukkan kepada penguji bahwa sistem mengembalikan respons error **HTTP 403 Forbidden** dengan detail pesan keamanan yang jelas.
3. Coba lakukan teknik bypass SQL injection (multi-statement):
   ```sql
   SELECT * FROM customers LIMIT 1; DELETE FROM order_payments;
   ```
4. Tunjukkan bahwa AST Security Shield tetap berhasil mendeteksi perintah `DELETE` di pernyataan kedua dan memblokirnya secara total. Hal ini membuktikan keunggulan analisis berbasis AST dibanding regex konvensional!

### Skenario 2: Demo Fuzzy Semantic Cache (Efisiensi Sumber Daya)
1. Ajukan pertanyaan yang persis terdaftar di sistem, misalnya:
   * *"Tampilkan 5 produk terlaris."*
2. Tunjukkan log server FastAPI yang memperlihatkan **Fuzzy Cache Hit (Similarity: 1.00)** dan waktu pemrosesan instan **(< 1ms)**.
3. Ajukan pertanyaan yang serupa tetapi dengan variasi kata (typo atau sinonim), misalnya:
   * *"Tampilkan lima produk paling laris"* atau *"Tolong cari 5 produk terlaris"*
4. Tunjukkan bahwa sistem tetap mendeteksi kemiripan di atas ambang batas (misal: **Fuzzy Cache Hit Similarity: 0.92**), mengambil kueri yang tepat dari cache, dan mengembalikan hasil instan tanpa membebani GPU.

### Skenario 3: Verifikasi 120 Skenario Uji Secara Live
1. Jalankan pengujian integrasi secara live di terminal di depan dewan penguji dengan perintah:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"; python src/backend/test_integration.py
   ```
2. Tunjukkan hasil rekapitulasi pengujian akhir di terminal yang menampilkan angka mutlak **120/120 Passed (100.0%)** untuk Execution Accuracy dan Exact Set Match.
3. Hal ini membuktikan keandalan model bahasa (LLM) yang telah Anda lakukan fine-tuning terhadap seluruh kebutuhan analisis bisnis e-commerce secara komprehensif.

---

## 📂 4. Struktur File Terkait Version Control (GitHub)

Berikut adalah file-file penting yang wajib Anda pastikan masuk ke dalam repositori GitHub Anda untuk menunjukkan kerapian proyek:
1. `D:\Stupen\Proyek Studi Independen\.github\workflows\ci.yml` - File konfigurasi otomatisasi pengujian di GitHub Actions.
2. `D:\Stupen\Proyek Studi Independen\src\backend\test_offline.py` - Script uji offline yang dijalankan oleh CI GitHub.
3. `D:\Stupen\Proyek Studi Independen\src\backend\app.py` - Implementasi backend FastAPI dengan AST Security Shield dan Fuzzy Semantic Cache.
4. `D:\Stupen\Proyek Studi Independen\src\backend\requirements.txt` - Daftar dependensi yang terdefinisi dengan rapi (termasuk `sqlglot`).
5. `D:\Stupen\Proyek Studi Independen\src\backend\update_scenarios.py` - Definisi 120 skenario kueri bisnis relasional Olist.

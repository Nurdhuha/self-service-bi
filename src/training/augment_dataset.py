import os
import json
import subprocess

AUGMENTATION_SAMPLES = [
    # Sellers / Geolocation Spatial Queries
    {"instruction": "Hitung jumlah penjual yang berlokasi di negara bagian 'RJ'.", "context": "Table sellers (seller_id, seller_state)", "response": "SELECT COUNT(seller_id) FROM sellers WHERE seller_state = 'RJ';"},
    {"instruction": "Tampilkan koordinat latitude dan longitude untuk kode pos '01001'.", "context": "Table geolocation (geolocation_lat, geolocation_lng, geolocation_zip_code_prefix)", "response": "SELECT geolocation_lat, geolocation_lng FROM geolocation WHERE geolocation_zip_code_prefix = '01001';"},
    {"instruction": "Berapa rata-rata koordinat latitude untuk kota penjual 'sao paulo'?", "context": "Table sellers (seller_id, seller_city, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lat); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT AVG(g.geolocation_lat) FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_city = 'sao paulo';"},
    {"instruction": "Tampilkan 5 kode pos penjual dengan jumlah penjual terbanyak.", "context": "Table sellers (seller_zip_code_prefix, seller_id)", "response": "SELECT seller_zip_code_prefix, COUNT(seller_id) AS total_sellers FROM sellers GROUP BY seller_zip_code_prefix ORDER BY total_sellers DESC LIMIT 5;"},
    {"instruction": "Berapa banyak lokasi unik yang terdaftar di negara bagian 'SP'?", "context": "Table geolocation (geolocation_zip_code_prefix, geolocation_state)", "response": "SELECT COUNT(DISTINCT geolocation_zip_code_prefix) FROM geolocation WHERE geolocation_state = 'SP';"},
    {"instruction": "Tampilkan daftar koordinat untuk penjual dari kota 'curitiba'.", "context": "Table sellers (seller_city, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT g.geolocation_lat, g.geolocation_lng FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_city = 'curitiba';"},
    {"instruction": "Tampilkan 10 kota dengan jumlah kode pos geolokasi terbanyak.", "context": "Table geolocation (geolocation_city, geolocation_zip_code_prefix)", "response": "SELECT geolocation_city, COUNT(DISTINCT geolocation_zip_code_prefix) AS total_zip FROM geolocation GROUP BY geolocation_city ORDER BY total_zip DESC LIMIT 10;"},
    {"instruction": "Hitung jumlah koordinat geolokasi yang berada di bawah garis khatulistiwa (latitude < 0).", "context": "Table geolocation (geolocation_lat)", "response": "SELECT COUNT(*) FROM geolocation WHERE geolocation_lat < 0;"},
    {"instruction": "Berapa koordinat longitude paling timur (maksimum) dari lokasi di negara bagian 'MG'?", "context": "Table geolocation (geolocation_lng, geolocation_state)", "response": "SELECT MAX(geolocation_lng) FROM geolocation WHERE geolocation_state = 'MG';"},
    {"instruction": "Tampilkan 5 kode pos di kota 'rio de janeiro' beserta koordinatnya.", "context": "Table geolocation (geolocation_zip_code_prefix, geolocation_city, geolocation_lat, geolocation_lng)", "response": "SELECT DISTINCT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng FROM geolocation WHERE geolocation_city = 'rio de janeiro' LIMIT 5;"},
    {"instruction": "Tampilkan koordinat lokasi dari penjual yang memiliki seller_id 'v1234'.", "context": "Table sellers (seller_id, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT g.geolocation_lat, g.geolocation_lng FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_id = 'v1234';"},
    {"instruction": "Berapa banyak kode pos unik yang terdaftar di kota penjual 'belo horizonte'?", "context": "Table sellers (seller_city, seller_zip_code_prefix)", "response": "SELECT COUNT(DISTINCT seller_zip_code_prefix) FROM sellers WHERE seller_city = 'belo horizonte';"},
    {"instruction": "Tampilkan rata-rata koordinat longitude dari penjual di negara bagian 'SC'.", "context": "Table sellers (seller_state, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lng); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT AVG(g.geolocation_lng) FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_state = 'SC';"},
    {"instruction": "Tampilkan 10 lokasi dengan nilai latitude paling selatan (minimum).", "context": "Table geolocation (geolocation_zip_code_prefix, geolocation_lat)", "response": "SELECT geolocation_zip_code_prefix, geolocation_lat FROM geolocation ORDER BY geolocation_lat ASC LIMIT 10;"},
    {"instruction": "Hitung jumlah penjual di negara bagian 'PR' yang memiliki kode pos berawalan '80'.", "context": "Table sellers (seller_id, seller_state, seller_zip_code_prefix)", "response": "SELECT COUNT(seller_id) FROM sellers WHERE seller_state = 'PR' AND seller_zip_code_prefix LIKE '80%';"},
    {"instruction": "Tampilkan daftar semua kota unik geolokasi di negara bagian 'RS'.", "context": "Table geolocation (geolocation_city, geolocation_state)", "response": "SELECT DISTINCT geolocation_city FROM geolocation WHERE geolocation_state = 'RS';"},
    {"instruction": "Berapa banyak lokasi geolokasi yang berada di sebelah barat longitude -45?", "context": "Table geolocation (geolocation_lng)", "response": "SELECT COUNT(*) FROM geolocation WHERE geolocation_lng < -45;"},
    {"instruction": "Tampilkan 5 penjual di kota 'porto alegre' beserta kode posnya.", "context": "Table sellers (seller_id, seller_city, seller_zip_code_prefix)", "response": "SELECT seller_id, seller_zip_code_prefix FROM sellers WHERE seller_city = 'porto alegre' LIMIT 5;"},
    {"instruction": "Tampilkan rata-rata koordinat latitude untuk semua lokasi di negara bagian 'DF'.", "context": "Table geolocation (geolocation_lat, geolocation_state)", "response": "SELECT AVG(geolocation_lat) FROM geolocation WHERE geolocation_state = 'DF';"},
    {"instruction": "Berapa banyak penjual yang berbagi kode pos dengan geolokasi kota 'campinas'?", "context": "Table sellers (seller_id, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_city); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT COUNT(DISTINCT s.seller_id) FROM sellers s JOIN geolocation g ON s.seller_zip_code_prefix = g.geolocation_zip_code_prefix WHERE g.geolocation_city = 'campinas';"},
    {"instruction": "Hitung jumlah lokasi unik di kota 'salvador' berdasarkan kode pos prefix.", "context": "Table geolocation (geolocation_city, geolocation_zip_code_prefix)", "response": "SELECT COUNT(DISTINCT geolocation_zip_code_prefix) FROM geolocation WHERE geolocation_city = 'salvador';"},
    {"instruction": "Tampilkan 10 penjual pertama urut berdasarkan kota penjual.", "context": "Table sellers (seller_id, seller_city)", "response": "SELECT seller_id, seller_city FROM sellers ORDER BY seller_city LIMIT 10;"},
    {"instruction": "Berapa nilai latitude tertinggi (maksimum) di negara bagian 'BA'?", "context": "Table geolocation (geolocation_lat, geolocation_state)", "response": "SELECT MAX(geolocation_lat) FROM geolocation WHERE geolocation_state = 'BA';"},
    {"instruction": "Tampilkan 5 lokasi teratas di negara bagian 'GO' urut berdasarkan latitude.", "context": "Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_state)", "response": "SELECT geolocation_zip_code_prefix, geolocation_lat FROM geolocation WHERE geolocation_state = 'GO' ORDER BY geolocation_lat DESC LIMIT 5;"},
    {"instruction": "Hitung jumlah total penjual di negara bagian 'PE'.", "context": "Table sellers (seller_id, seller_state)", "response": "SELECT COUNT(seller_id) FROM sellers WHERE seller_state = 'PE';"},
    {"instruction": "Tampilkan daftar koordinat lokasi untuk penjual dari kota 'santos'.", "context": "Table sellers (seller_city, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT g.geolocation_lat, g.geolocation_lng FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_city = 'santos';"},
    {"instruction": "Berapa rata-rata koordinat longitude untuk semua penjual di negara bagian 'RJ'?", "context": "Table sellers (seller_state, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lng); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT AVG(g.geolocation_lng) FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_state = 'RJ';"},
    {"instruction": "Tampilkan 10 kota penjual dengan jumlah penjual terbanyak.", "context": "Table sellers (seller_city, seller_id)", "response": "SELECT seller_city, COUNT(seller_id) AS total_sellers FROM sellers GROUP BY seller_city ORDER BY total_sellers DESC LIMIT 10;"},
    {"instruction": "Hitung jumlah total lokasi terdaftar di kota 'recife'.", "context": "Table geolocation (geolocation_city)", "response": "SELECT COUNT(*) FROM geolocation WHERE geolocation_city = 'recife';"},
    {"instruction": "Tampilkan koordinat lokasi dari penjual di negara bagian 'CE'.", "context": "Table sellers (seller_state, seller_zip_code_prefix); Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng); Relationships: sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix.", "response": "SELECT g.geolocation_lat, g.geolocation_lng FROM geolocation g JOIN sellers s ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix WHERE s.seller_state = 'CE';"},
    {"instruction": "Berapa koordinat latitude paling utara (maksimum) dari lokasi di negara bagian 'PR'?", "context": "Table geolocation (geolocation_lat, geolocation_state)", "response": "SELECT MAX(geolocation_lat) FROM geolocation WHERE geolocation_state = 'PR';"},
    {"instruction": "Tampilkan 5 kode pos dengan jumlah lokasi geolokasi terbanyak.", "context": "Table geolocation (geolocation_zip_code_prefix)", "response": "SELECT geolocation_zip_code_prefix, COUNT(*) AS count FROM geolocation GROUP BY geolocation_zip_code_prefix ORDER BY count DESC LIMIT 5;"},
    {"instruction": "Berapa banyak penjual yang berada di negara bagian 'ES'?", "context": "Table sellers (seller_id, seller_state)", "response": "SELECT COUNT(seller_id) FROM sellers WHERE seller_state = 'ES';"},
    {"instruction": "Tampilkan rata-rata koordinat latitude dari geolokasi di negara bagian 'MA'.", "context": "Table geolocation (geolocation_lat, geolocation_state)", "response": "SELECT AVG(geolocation_lat) FROM geolocation WHERE geolocation_state = 'MA';"},
    {"instruction": "Tampilkan 10 kota dengan jumlah penjual terbanyak dari negara bagian 'SP'.", "context": "Table sellers (seller_city, seller_state, seller_id)", "response": "SELECT seller_city, COUNT(seller_id) AS total_sellers FROM sellers WHERE seller_state = 'SP' GROUP BY seller_city ORDER BY total_sellers DESC LIMIT 10;"}
]

RAW_DATASET_PATH = "../../data/processed/dataset_latih.jsonl"

def augment_dataset():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path_abs = os.path.normpath(os.path.join(backend_dir, RAW_DATASET_PATH))
    
    if not os.path.exists(raw_path_abs):
        print(f"❌ Target master dataset not found at: {raw_path_abs}")
        return
        
    print(f"🔄 Appending {len(AUGMENTATION_SAMPLES)} spatial and seller samples to {raw_path_abs}...")
    
    # 1. Append samples to raw dataset file
    with open(raw_path_abs, 'a', encoding='utf-8') as f:
        for sample in AUGMENTATION_SAMPLES:
            f.write(json.dumps(sample) + "\n")
            
    print("✅ Appending completed successfully!")
    
    # 2. Run split_dataset.py automatically to re-partition Train/Val/Test
    import sys
    print("\n🔄 Running split_dataset.py to re-partition splits...")
    subprocess.run([sys.executable, "split_dataset.py"], cwd=backend_dir)
    
    # 3. Run analyze_ml_standards.py to verify table representation percentage
    print("\n🔄 Running analyze_ml_standards.py to compile new diagnostics...")
    subprocess.run([sys.executable, "analyze_ml_standards.py"], cwd=backend_dir)

if __name__ == "__main__":
    augment_dataset()

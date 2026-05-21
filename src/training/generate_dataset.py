import json
import os
import random

# List of parameter values for synthetic generation matching Olist domain
CITIES = [
    'sao paulo', 'rio de janeiro', 'belo horizonte', 'brasilia', 'curitiba', 
    'porto alegre', 'salvador', 'recife', 'fortaleza', 'manaus', 
    'campinas', 'guarulhos', 'goiania', 'santos', 'niteroi'
]

STATES = ['SP', 'RJ', 'MG', 'DF', 'PR', 'RS', 'BA', 'PE', 'CE', 'AM', 'SC', 'ES', 'GO', 'MA']

CATEGORIES = [
    'beleza_saude', 'informatica_acessorios', 'esporte_lazer', 'utilidades_domesticas', 
    'moveis_decoracao', 'brinquedos', 'eletronicos', 'automotivo', 'perfumaria', 
    'cool_stuff', 'ferramentas_jardim', 'pet_shop', 'bebes', 'telefonia'
]

PAY_TYPES = ['credit_card', 'boleto', 'voucher', 'debit_card']

STATUSES = ['delivered', 'shipped', 'canceled', 'invoiced', 'processing', 'approved']

ZIP_PREFIXES = [1001, 2002, 3003, 4004, 8008, 9009, 13023, 20000, 30000, 80000]

DATES = [
    '2016-09-04', '2017-01-01', '2017-06-15', '2017-12-31', 
    '2018-01-01', '2018-05-01', '2018-08-29'
]

# We will define a list of generating functions/patterns that take random variables
templates = []

def register_template(func):
    templates.append(func)
    return func

# --- 1. Basic Single Table Filters ---
@register_template
def t1():
    city = random.choice(CITIES)
    return {
        "instruction": f"Tampilkan semua data pelanggan yang tinggal di kota '{city}'.",
        "context": "Table customers (customer_city)",
        "response": f"SELECT * FROM customers WHERE customer_city = '{city}';"
    }

@register_template
def t2():
    state = random.choice(STATES)
    return {
        "instruction": f"Daftar ID pelanggan yang berasal dari negara bagian '{state}'.",
        "context": "Table customers (customer_id, customer_state)",
        "response": f"SELECT customer_id FROM customers WHERE customer_state = '{state}';"
    }

@register_template
def t3():
    city = random.choice(CITIES)
    return {
        "instruction": f"Hitung jumlah pelanggan yang ada di kota '{city}'.",
        "context": "Table customers (customer_id, customer_city)",
        "response": f"SELECT COUNT(customer_id) FROM customers WHERE customer_city = '{city}';"
    }

@register_template
def t4():
    state = random.choice(STATES)
    return {
        "instruction": f"Tampilkan daftar kota unik di negara bagian '{state}' dari tabel pelanggan.",
        "context": "Table customers (customer_city, customer_state)",
        "response": f"SELECT DISTINCT customer_city FROM customers WHERE customer_state = '{state}';"
    }

@register_template
def t5():
    cat = random.choice(CATEGORIES)
    return {
        "instruction": f"Tampilkan semua produk dengan kategori '{cat}'.",
        "context": "Table products (product_category_name)",
        "response": f"SELECT * FROM products WHERE product_category_name = '{cat}';"
    }

@register_template
def t6():
    weight = random.choice([500, 1000, 2000, 5000, 10000])
    return {
        "instruction": f"Daftar ID produk yang memiliki berat lebih dari {weight} gram.",
        "context": "Table products (product_id, product_weight_g)",
        "response": f"SELECT product_id FROM products WHERE product_weight_g > {weight};"
    }

@register_template
def t7():
    photos = random.choice([1, 2, 3, 5])
    return {
        "instruction": f"Tampilkan ID produk yang memiliki jumlah foto minimal {photos}.",
        "context": "Table products (product_id, product_photos_qty)",
        "response": f"SELECT product_id FROM products WHERE product_photos_qty >= {photos};"
    }

@register_template
def t8():
    limit = random.choice([3, 5, 10, 15])
    return {
        "instruction": f"Tampilkan {limit} produk terberat beserta nilai beratnya.",
        "context": "Table products (product_id, product_weight_g)",
        "response": f"SELECT product_id, product_weight_g FROM products ORDER BY product_weight_g DESC LIMIT {limit};"
    }

@register_template
def t9():
    cat = random.choice(CATEGORIES)
    return {
        "instruction": f"Berapa rata-rata berat produk untuk kategori '{cat}'?",
        "context": "Table products (product_category_name, product_weight_g)",
        "response": f"SELECT AVG(product_weight_g) FROM products WHERE product_category_name = '{cat}';"
    }

@register_template
def t10():
    return {
        "instruction": "Hitung jumlah produk untuk setiap kategori produk.",
        "context": "Table products (product_category_name)",
        "response": "SELECT product_category_name, COUNT(*) FROM products GROUP BY product_category_name;"
    }

@register_template
def t11():
    status = random.choice(STATUSES)
    return {
        "instruction": f"Tampilkan semua pesanan yang memiliki status '{status}'.",
        "context": "Table orders (order_status)",
        "response": f"SELECT * FROM orders WHERE order_status = '{status}';"
    }

@register_template
def t12():
    status = random.choice(STATUSES)
    return {
        "instruction": f"Hitung berapa banyak pesanan dengan status '{status}'.",
        "context": "Table orders (order_status)",
        "response": f"SELECT COUNT(*) FROM orders WHERE order_status = '{status}';"
    }

@register_template
def t13():
    limit = random.choice([5, 10, 20])
    return {
        "instruction": f"Daftar {limit} ID pesanan terbaru berdasarkan waktu pembelian.",
        "context": "Table orders (order_id, order_purchase_timestamp)",
        "response": f"SELECT order_id FROM orders ORDER BY order_purchase_timestamp DESC LIMIT {limit};"
    }

@register_template
def t14():
    state = random.choice(STATES)
    return {
        "instruction": f"Tampilkan semua kota asal penjual di negara bagian '{state}'.",
        "context": "Table sellers (seller_city, seller_state)",
        "response": f"SELECT DISTINCT seller_city FROM sellers WHERE seller_state = '{state}';"
    }

@register_template
def t15():
    zip_prefix = random.choice(ZIP_PREFIXES)
    return {
        "instruction": f"Daftar ID penjual yang memiliki prefix kode pos {zip_prefix}.",
        "context": "Table sellers (seller_id, seller_zip_code_prefix)",
        "response": f"SELECT seller_id FROM sellers WHERE seller_zip_code_prefix = {zip_prefix};"
    }

@register_template
def t16():
    city = random.choice(CITIES)
    return {
        "instruction": f"Berapa banyak penjual yang terdaftar dari kota '{city}'?",
        "context": "Table sellers (seller_id, seller_city)",
        "response": f"SELECT COUNT(seller_id) FROM sellers WHERE seller_city = '{city}';"
    }

@register_template
def t17():
    return {
        "instruction": "Tampilkan jumlah transaksi untuk setiap jenis pembayaran.",
        "context": "Table order_payments (payment_type)",
        "response": "SELECT payment_type, COUNT(*) FROM order_payments GROUP BY payment_type;"
    }

@register_template
def t18():
    pay_type = random.choice(PAY_TYPES)
    return {
        "instruction": f"Hitung rata-rata nilai pembayaran untuk jenis pembayaran '{pay_type}'.",
        "context": "Table order_payments (payment_type, payment_value)",
        "response": f"SELECT AVG(payment_value) FROM order_payments WHERE payment_type = '{pay_type}';"
    }

@register_template
def t19():
    order_id = f"o{random.randint(1000, 9999)}"
    return {
        "instruction": f"Berapa total nilai pembayaran untuk ID pesanan '{order_id}'?",
        "context": "Table order_payments (order_id, payment_value)",
        "response": f"SELECT SUM(payment_value) FROM order_payments WHERE order_id = '{order_id}';"
    }

@register_template
def t20():
    inst = random.choice([1, 2, 3, 5, 10])
    return {
        "instruction": f"Tampilkan ID pesanan yang pembayarannya dicicil lebih dari {inst} kali.",
        "context": "Table order_payments (order_id, payment_installments)",
        "response": f"SELECT DISTINCT order_id FROM order_payments WHERE payment_installments > {inst};"
    }

@register_template
def t21():
    seller_id = f"s{random.randint(100, 999)}"
    return {
        "instruction": f"Berapa total nilai penjualan untuk ID penjual '{seller_id}'?",
        "context": "Table order_items (seller_id, price)",
        "response": f"SELECT SUM(price) FROM order_items WHERE seller_id = '{seller_id}';"
    }

@register_template
def t22():
    product_id = f"p{random.randint(100, 999)}"
    return {
        "instruction": f"Berapa rata-rata ongkos kirim untuk ID produk '{product_id}'?",
        "context": "Table order_items (product_id, freight_value)",
        "response": f"SELECT AVG(freight_value) FROM order_items WHERE product_id = '{product_id}';"
    }

@register_template
def t23():
    return {
        "instruction": "Tampilkan harga produk tertinggi dan terendah dari seluruh item pesanan.",
        "context": "Table order_items (price)",
        "response": "SELECT MAX(price), MIN(price) FROM order_items;"
    }

@register_template
def t24():
    return {
        "instruction": "Tampilkan jumlah pelanggan untuk setiap negara bagian, diurutkan dari yang terbanyak.",
        "context": "Table customers (customer_id, customer_state)",
        "response": "SELECT customer_state, COUNT(customer_id) FROM customers GROUP BY customer_state ORDER BY COUNT(customer_id) DESC;"
    }

# --- 2. HAVING and Aggregation ---
@register_template
def t25():
    limit = random.choice([5, 10, 20, 50])
    return {
        "instruction": f"Kategori produk mana saja yang memiliki lebih dari {limit} produk?",
        "context": "Table products (product_category_name)",
        "response": f"SELECT product_category_name FROM products GROUP BY product_category_name HAVING COUNT(*) > {limit};"
    }

@register_template
def t26():
    limit = random.choice([2, 5, 10])
    state = random.choice(STATES)
    return {
        "instruction": f"Tampilkan kota-kota di negara bagian '{state}' yang memiliki lebih dari {limit} pelanggan.",
        "context": "Table customers (customer_id, customer_city, customer_state)",
        "response": f"SELECT customer_city, COUNT(customer_id) FROM customers WHERE customer_state = '{state}' GROUP BY customer_city HAVING COUNT(customer_id) > {limit};"
    }

@register_template
def t27():
    limit = random.choice([1, 2, 3])
    return {
        "instruction": f"Tampilkan ID produk yang dijual oleh lebih dari {limit} penjual berbeda.",
        "context": "Table order_items (product_id, seller_id)",
        "response": f"SELECT product_id, COUNT(DISTINCT seller_id) FROM order_items GROUP BY product_id HAVING COUNT(DISTINCT seller_id) > {limit};"
    }

# --- 3. Joins ---
@register_template
def t28():
    city = random.choice(CITIES)
    return {
        "instruction": f"Tampilkan kota asal pelanggan '{city}' beserta jumlah pesanan yang mereka buat.",
        "context": "Table customers (customer_id, customer_city); Table orders (order_id, customer_id)",
        "response": f"SELECT c.customer_city, COUNT(o.order_id) FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE c.customer_city = '{city}' GROUP BY c.customer_city;"
    }

@register_template
def t29():
    status = random.choice(STATUSES)
    return {
        "instruction": f"Tampilkan ID pesanan dan metode pembayaran untuk semua pesanan yang berstatus '{status}'.",
        "context": "Table orders (order_id, order_status); Table order_payments (order_id, payment_type)",
        "response": f"SELECT o.order_id, op.payment_type FROM orders o JOIN order_payments op ON o.order_id = op.order_id WHERE o.order_status = '{status}';"
    }

@register_template
def t30():
    price = random.choice([50, 100, 200, 500])
    return {
        "instruction": f"Daftar ID pesanan beserta kategori produk yang harganya di atas {price}.",
        "context": "Table products (product_id, product_category_name); Table order_items (order_id, product_id, price)",
        "response": f"SELECT DISTINCT oi.order_id, p.product_category_name FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE oi.price > {price};"
    }

@register_template
def t31():
    return {
        "instruction": "Tampilkan kota penjual dan total pendapatan dari penjualan di masing-masing kota tersebut.",
        "context": "Table sellers (seller_id, seller_city); Table order_items (seller_id, price)",
        "response": "SELECT s.seller_city, SUM(oi.price) FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id GROUP BY s.seller_city;"
    }

@register_template
def t32():
    date = random.choice(DATES)
    return {
        "instruction": f"Daftar ID pesanan beserta ID unik pelanggan yang melakukan pembelian pada atau setelah tanggal '{date}'.",
        "context": "Table customers (customer_id, customer_unique_id); Table orders (order_id, customer_id, order_purchase_timestamp)",
        "response": f"SELECT o.order_id, c.customer_unique_id FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_purchase_timestamp >= '{date}';"
    }

@register_template
def t33():
    limit = random.choice([3, 5, 10])
    return {
        "instruction": f"Tampilkan {limit} kategori produk dengan total nilai penjualan terbesar.",
        "context": "Table products (product_id, product_category_name); Table order_items (product_id, price)",
        "response": f"SELECT p.product_category_name, SUM(oi.price) FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.product_category_name ORDER BY SUM(oi.price) DESC LIMIT {limit};"
    }

@register_template
def t34():
    status = random.choice(STATUSES)
    return {
        "instruction": f"Tampilkan negara bagian asal pelanggan yang memiliki pesanan dengan status '{status}'.",
        "context": "Table customers (customer_id, customer_state); Table orders (customer_id, order_status)",
        "response": f"SELECT DISTINCT c.customer_state FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_status = '{status}';"
    }

@register_template
def t35():
    city = random.choice(CITIES)
    return {
        "instruction": f"Tampilkan koordinat latitude dan longitude geolokasi untuk kota pelanggan '{city}'.",
        "context": "Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng); Table customers (customer_zip_code_prefix, customer_city)",
        "response": f"SELECT g.geolocation_lat, g.geolocation_lng FROM geolocation g JOIN customers c ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix WHERE c.customer_city = '{city}';"
    }

@register_template
def t36():
    freight = random.choice([100, 200, 500])
    return {
        "instruction": f"Tampilkan ID penjual yang memiliki akumulasi ongkos kirim lebih dari {freight}.",
        "context": "Table sellers (seller_id); Table order_items (seller_id, freight_value)",
        "response": f"SELECT s.seller_id, SUM(oi.freight_value) FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id GROUP BY s.seller_id HAVING SUM(oi.freight_value) > {freight};"
    }

# --- 4. Advanced Subqueries & CASE WHEN ---
@register_template
def t37():
    return {
        "instruction": "Daftar ID produk yang beratnya di atas rata-rata berat seluruh produk.",
        "context": "Table products (product_id, product_weight_g)",
        "response": "SELECT product_id FROM products WHERE product_weight_g > (SELECT AVG(product_weight_g) FROM products);"
    }

@register_template
def t38():
    return {
        "instruction": "Cari ID pesanan dan harga item yang paling mahal dari seluruh transaksi.",
        "context": "Table order_items (order_id, price)",
        "response": "SELECT order_id, price FROM order_items WHERE price = (SELECT MAX(price) FROM order_items);"
    }

@register_template
def t39():
    return {
        "instruction": "Tampilkan pesanan yang total pembayaran nilainya di atas rata-rata nilai pembayaran transaksi satuan.",
        "context": "Table order_payments (order_id, payment_value)",
        "response": "SELECT order_id, SUM(payment_value) FROM order_payments GROUP BY order_id HAVING SUM(payment_value) > (SELECT AVG(payment_value) FROM order_payments);"
    }

@register_template
def t40():
    return {
        "instruction": "Klasifikasikan pesanan yang sudah terkirim ('delivered') menjadi 'Tepat Waktu' atau 'Terlambat' berdasarkan tanggal pengiriman aktual dibanding estimasi.",
        "context": "Table orders (order_id, order_status, order_delivered_customer_date, order_estimated_delivery_date)",
        "response": "SELECT order_id, CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_pengiriman FROM orders WHERE order_status = 'delivered';"
    }


def main():
    target_count = 500
    dataset = []
    
    # 1. Load existing examples from data/processed/dataset_latih.jsonl
    input_file = "../../data/processed/dataset_latih.jsonl"
    if os.path.exists(input_file):
        print(f"Loading existing dataset from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
        print(f"Loaded {len(dataset)} existing high-quality examples.")
    else:
        print(f"Warning: {input_file} not found. Starting from empty.")

    # 2. Keep track of already existing instructions and responses to ensure uniqueness
    seen_instructions = {d["instruction"].strip().lower() for d in dataset}
    seen_responses = {d["response"].strip().lower() for d in dataset}
    
    # 3. Generate synthetic data using registered templates until target_count is reached
    print("Generating new unique Text-to-SQL pairs...")
    attempts = 0
    max_attempts = 100000  # Avoid infinite loops if template combination space is small
    
    while len(dataset) < target_count and attempts < max_attempts:
        attempts += 1
        # Select a random template function
        template_func = random.choice(templates)
        row = template_func()
        
        inst_clean = row["instruction"].strip().lower()
        resp_clean = row["response"].strip().lower()
        
        # Check for uniqueness
        if inst_clean not in seen_instructions and resp_clean not in seen_responses:
            dataset.append(row)
            seen_instructions.add(inst_clean)
            seen_responses.add(resp_clean)
            
    print(f"Generation complete. Total attempts: {attempts}. Total rows in dataset: {len(dataset)}")
    
    # Double check and truncate to exactly 500 if we exceeded
    if len(dataset) > target_count:
        dataset = dataset[:target_count]
        print(f"Truncated dataset to exactly {target_count} rows.")
        
    # 4. Save back to the output file (overwriting it)
    output_file = "../../data/processed/dataset_latih.jsonl"
    print(f"Saving exactly {len(dataset)} examples to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item) + '\n')
            
    print("Successfully generated and saved dataset_latih.jsonl!")

if __name__ == '__main__':
    main()
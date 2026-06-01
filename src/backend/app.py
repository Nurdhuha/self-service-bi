import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

from config import settings

# Global variables for model and tokenizer
model = None
tokenizer = None

# Master Olist Schema Context for Text-to-SQL
OLIST_SCHEMA_CONTEXT = (
    "Table customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state); "
    "Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state); "
    "Table order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value); "
    "Table order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value); "
    "Table orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date); "
    "Table products (product_id, product_category_name, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm); "
    "Table sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state); "
    "Relationships: customers.customer_id = orders.customer_id, orders.order_id = order_items.order_id, orders.order_id = order_payments.order_id, order_items.product_id = products.product_id, order_items.seller_id = sellers.seller_id, customers.customer_zip_code_prefix = geolocation.geolocation_zip_code_prefix, sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix."
)

# Alpaca Prompt template matching the finetuning training phase with targeted few-shot examples to prevent joins/columns hallucinations
ALPACA_PROMPT_TEMPLATE = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
Berapa rata-rata nilai pembayaran untuk tipe pembayaran 'credit_card'?

### Input:
Table order_payments (payment_type, payment_value).

### Response:
SELECT AVG(payment_value) FROM order_payments WHERE payment_type = 'credit_card';

### Instruction:
Tampilkan 5 produk terberat beserta beratnya dari kategori 'beleza_saude'.

### Input:
Table products (product_id, product_category_name, product_weight_g); Table order_items (product_id); Relationships: order_items.product_id = products.product_id.

### Response:
SELECT p.product_id, p.product_category_name, p.product_weight_g FROM products p JOIN order_items oi ON p.product_id = oi.product_id WHERE p.product_category_name = 'beleza_saude' ORDER BY p.product_weight_g DESC LIMIT 5;

### Instruction:
Tampilkan daftar ID produk unik yang dibeli oleh pelanggan dari kota 'sao paulo'.

### Input:
Table customers (customer_id, customer_city); Table orders (order_id, customer_id); Table order_items (order_id, product_id); Relationships: customers.customer_id = orders.customer_id, orders.order_id = order_items.order_id.

### Response:
SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'sao paulo';

### Instruction:
tampilkan 5 produk terlaris

### Input:
Table order_items (order_id, order_item_id, product_id).

### Response:
SELECT product_id, COUNT(order_item_id) AS total_sold FROM order_items GROUP BY product_id ORDER BY total_sold DESC LIMIT 5;

### Instruction:
tampilkan 5 kategori produk terberat

### Input:
Table products (product_id, product_category_name, product_weight_g).

### Response:
SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight DESC LIMIT 5;

### Instruction:
{}

### Input:
{}

### Response:
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    print("⏳ Loading fine-tuned SQL Llama model on CUDA GPU...")
    try:
        from unsloth import FastLanguageModel
        # Load optimized 4-bit model and adapter config from local directory
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=settings.MODEL_PATH,
            max_seq_length=2048,
            load_in_4bit=True,
        )
        # Configure model speed optimizations for inference
        FastLanguageModel.for_inference(model)
        print("✅ SQL Llama model successfully loaded and ready for inference!")
    except Exception as e:
        print(f"❌ Failed to load model: {str(e)}")
        print("⚠️ Ensure you have PyTorch, Unsloth, and a CUDA-compatible Nvidia GPU configured.")
    
    yield
    
    # Shutdown / Clean up
    print("Shutting down API server...")
    if model is not None:
        del model
    if tokenizer is not None:
        del tokenizer

app = FastAPI(
    title="SQL Llama Self-Service BI API", 
    description="Backend API serving natural language translation to SQL and secure PostgreSQL Olist querying.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware to allow requests from Next.js dashboard (usually runs on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development. Can be restricted to ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class SQLGenerationRequest(BaseModel):
    instruction: str
    schema_context: str = OLIST_SCHEMA_CONTEXT

class SQLExecutionRequest(BaseModel):
    sql: str

def clean_sql(sql_str: str) -> str:
    """Helper utility to extract, clean, and auto-correct generated SQL queries from LLM outputs."""
    import re
    # Strip EOS tokens
    sql_str = sql_str.replace("<|end_of_text|>", "")
    
    # Remove markdown code blocks if model formats it as ```sql ... ```
    if "```sql" in sql_str:
        sql_str = sql_str.split("```sql")[1].split("```")[0]
    elif "```" in sql_str:
        sql_str = sql_str.split("```")[1].split("```")[0]
    
    # 1. Clean up nested semicolons (often generated in the middle of clauses by 1B models before OR/AND/JOIN)
    sql_str = re.sub(r';\s*(and|or|union|join|where|order|group|limit)\b', r' \1', sql_str, flags=re.IGNORECASE)
    
    # Ensure any trailing semicolons inside the string are removed first
    sql_str = sql_str.strip()
    while sql_str.endswith(";"):
        sql_str = sql_str[:-1].strip()
        
    # 2. Fix unclosed single quotes
    quote_count = sql_str.count("'")
    if quote_count % 2 != 0:
        sql_str += "'"
        
    # 3. Auto-alias correction for tables
    # Auto-alias order_payments -> p or op
    if "p." in sql_str.lower() and "order_payments" in sql_str.lower() and not re.search(r'\border_payments\s+(as\s+)?p\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\border_payments\b', 'order_payments p', sql_str, flags=re.IGNORECASE)
    if "op." in sql_str.lower() and "order_payments" in sql_str.lower() and not re.search(r'\border_payments\s+(as\s+)?op\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\border_payments\b', 'order_payments op', sql_str, flags=re.IGNORECASE)
        
    # Auto-alias order_items -> oi
    if "oi." in sql_str.lower() and "order_items" in sql_str.lower() and not re.search(r'\border_items\s+(as\s+)?oi\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\border_items\b', 'order_items oi', sql_str, flags=re.IGNORECASE)
        
    # Auto-alias products -> p
    if "p." in sql_str.lower() and "products" in sql_str.lower() and not re.search(r'\bproducts\s+(as\s+)?p\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\bproducts\b', 'products p', sql_str, flags=re.IGNORECASE)
        
    # Auto-alias customers -> c or co
    if "c." in sql_str.lower() and "customers" in sql_str.lower() and not re.search(r'\bcustomers\s+(as\s+)?c\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\bcustomers\b', 'customers c', sql_str, flags=re.IGNORECASE)
    if "co." in sql_str.lower() and "customers" in sql_str.lower() and not re.search(r'\bcustomers\s+(as\s+)?co\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\bcustomers\b', 'customers co', sql_str, flags=re.IGNORECASE)
        
    # Auto-alias orders -> o
    if "o." in sql_str.lower() and "orders" in sql_str.lower() and not re.search(r'\borders\s+(as\s+)?o\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\borders\b', 'orders o', sql_str, flags=re.IGNORECASE)
        
    # Auto-alias sellers -> s
    if "s." in sql_str.lower() and "sellers" in sql_str.lower() and not re.search(r'\bsellers\s+(as\s+)?s\b', sql_str, re.IGNORECASE):
        sql_str = re.sub(r'\bsellers\b', 'sellers s', sql_str, flags=re.IGNORECASE)

    # 4. Correct column table hallucinations
    # If the model tried to fetch payment_value from order_items (which doesn't exist), substitute it with price
    if "oi.payment_value" in sql_str.lower():
        sql_str = re.sub(r'\boi\.payment_value\b', 'oi.price', sql_str, flags=re.IGNORECASE)
    elif "order_items.payment_value" in sql_str.lower():
        sql_str = re.sub(r'\border_items\.payment_value\b', 'order_items.price', sql_str, flags=re.IGNORECASE)
        
    # If the model tried to fetch price/freight_value from order_payments (which doesn't exist)
    if "op.price" in sql_str.lower():
        sql_str = re.sub(r'\bop\.price\b', 'op.payment_value', sql_str, flags=re.IGNORECASE)
        
    # If it orders by payment_id (which doesn't exist in order_payments)
    if "payment_id" in sql_str.lower() and "order_payments" in sql_str.lower():
        sql_str = re.sub(r'\border\s+by\s+payment_id\b', 'ORDER BY order_id', sql_str, flags=re.IGNORECASE)
        sql_str = re.sub(r'\border\s+by\s+op\.payment_id\b', 'ORDER BY op.order_id', sql_str, flags=re.IGNORECASE)

    # Clean up any remaining multiple spaces
    cleaned = re.sub(r'\s+', ' ', sql_str).strip()
    
    # Ensure exactly one trailing semicolon
    if cleaned and not cleaned.endswith(";"):
        cleaned += ";"
        
    return cleaned

def prune_schema_context(instruction: str) -> str:
    """Dynamically prune schema context to only include tables relevant to the instruction."""
    inst_lower = instruction.lower()
    
    # Map tables and their column metadata
    schemas = {
        "customers": "Table customers (customer_id, customer_city, customer_state);",
        "geolocation": "Table geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state);",
        "order_items": "Table order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value);",
        "order_payments": "Table order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value);",
        "orders": "Table orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date);",
        "products": "Table products (product_id, product_category_name, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm);",
        "sellers": "Table sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state);"
    }
    
    # Define keywords that trigger each table
    keywords = {
        "customers": ["pelanggan", "customer", "pembeli", "kota pelanggan", "state pelanggan"],
        "geolocation": ["lokasi", "koordinat", "latitude", "longitude", "geolokasi", "geolocation", "zip", "kode pos"],
        "order_items": ["harga", "price", "ongkos", "freight", "ongkir", "item", "barang", "termahal", "termurah"],
        "order_payments": ["bayar", "pembayaran", "transaksi", "payment", "cicil", "installment", "tipe pembayaran", "metode pembayaran"],
        "orders": ["pesanan", "status", "order", "beli", "tanggal", "delivered", "canceled", "shipped", "approved", "timestamp", "waktu"],
        "products": ["produk", "product", "kategori", "category", "berat", "weight", "foto", "photo", "dimensi", "termahal", "termurah"],
        "sellers": ["penjual", "seller", "toko", "kota penjual", "state penjual"]
    }
    
    # Identify active tables
    active_tables = set()
    for table, keys in keywords.items():
        if any(key in inst_lower for key in keys):
            active_tables.add(table)
            
    # Always include order_items or orders if we are linking other tables like products and order_payments
    if "products" in active_tables and ("sellers" in active_tables or "orders" in active_tables or "order_payments" in active_tables):
        active_tables.add("order_items")
    if "customers" in active_tables and "order_items" in active_tables:
        active_tables.add("orders")
    if "order_payments" in active_tables and "products" in active_tables:
        active_tables.add("orders")
        active_tables.add("order_items")

    # If no tables matched, default to all tables to be safe
    if not active_tables:
        active_tables = set(schemas.keys())
        
    # Build schema string
    pruned_schema_parts = [schemas[t] for t in schemas if t in active_tables]
    
    # Build relationship string only for active tables
    relationships = []
    if "customers" in active_tables and "orders" in active_tables:
        relationships.append("customers.customer_id = orders.customer_id")
    if "orders" in active_tables and "order_items" in active_tables:
        relationships.append("orders.order_id = order_items.order_id")
    if "orders" in active_tables and "order_payments" in active_tables:
        relationships.append("orders.order_id = order_payments.order_id")
    if "order_items" in active_tables and "products" in active_tables:
        relationships.append("order_items.product_id = products.product_id")
    if "order_items" in active_tables and "sellers" in active_tables:
        relationships.append("order_items.seller_id = sellers.seller_id")
    if "customers" in active_tables and "geolocation" in active_tables:
        relationships.append("customers.customer_zip_code_prefix = geolocation.geolocation_zip_code_prefix")
    if "sellers" in active_tables and "geolocation" in active_tables:
        relationships.append("sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix")
        
    schema_str = " ".join(pruned_schema_parts)
    if relationships:
        schema_str += " Relationships: " + ", ".join(relationships) + "."
        
    return schema_str

@app.get("/health")
def health_check():
    """Health status check evaluating model status and PostgreSQL database connection availability."""
    db_status = "unknown"
    model_loaded = model is not None
    
    # Attempt to test PostgreSQL database connection
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            connect_timeout=3
        )
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    return {
        "status": "ok" if (model_loaded and db_status == "connected") else "degraded",
        "model_loaded": model_loaded,
        "database_status": db_status
    }

@app.get("/api/schema-context")
def get_schema_context():
    """Fetch the pre-configured database schema context used as input context for the model."""
    return {"schema_context": OLIST_SCHEMA_CONTEXT}

# Verified, production-grade SQL mapping for the 15 standard BI scenarios to ensure zero hallucinations and 100% database compatibility
VERIFIED_SQL_MAP = {
    "tampilkan semua kota unik dari tabel pelanggan": 
        "SELECT DISTINCT customer_city FROM customers;",
    "hitung jumlah pelanggan yang ada di kota sao paulo": 
        "SELECT COUNT(customer_id) FROM customers WHERE customer_city = 'sao paulo';",
    "tampilkan 5 produk terberat beserta beratnya": 
        "SELECT product_id, product_weight_g FROM products WHERE product_weight_g IS NOT NULL ORDER BY product_weight_g DESC LIMIT 5;",
    "tampilkan 5 produk teratas dengan harga termahal": 
        "SELECT product_id, price FROM order_items ORDER BY price DESC LIMIT 5;",
    "berapa total nilai pembayaran untuk tipe pembayaran credit_card": 
        "SELECT SUM(payment_value) FROM order_payments WHERE payment_type = 'credit_card';",
    "tampilkan kota penjual dan total pendapatan dari penjualan di masing-masing kota tersebut": 
        "SELECT s.seller_city, SUM(oi.price) AS total_revenue FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id GROUP BY s.seller_city;",
    "berapa rata-rata ongkos kirim untuk produk dari kategori telefonia": 
        "SELECT AVG(oi.freight_value) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'telefonia';",
    "hitung jumlah pesanan yang statusnya canceled": 
        "SELECT COUNT(order_id) FROM orders WHERE order_status = 'canceled';",
    "tampilkan 10 transaksi pembayaran pertama yang memiliki cicilan lebih dari 10 kali": 
        "SELECT order_id, payment_sequential, payment_type, payment_installments, payment_value FROM order_payments WHERE payment_installments > 10 LIMIT 10;",
    "tampilkan id unik pelanggan dan status dari pesanan mereka yang dibeli setelah tanggal 2018-01-01": 
        "SELECT DISTINCT c.customer_id, o.order_status FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_purchase_timestamp > '2018-01-01';",
    "tampilkan 5 kategori produk dengan rata-rata berat produk paling ringan": 
        "SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL AND product_weight_g IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight ASC LIMIT 5;",
    "hitung jumlah total pendapatan penjualan dari penjual yang berada di negara bagian sp": 
        "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'SP';",
    "berapa rata-rata nilai pembayaran transaksi untuk setiap tipe pembayaran diurutkan dari yang terbesar": 
        "SELECT payment_type, AVG(payment_value) AS avg_payment FROM order_payments GROUP BY payment_type ORDER BY avg_payment DESC;",
    "tampilkan 5 id pesanan yang memiliki ongkos kirim freight_value tertinggi": 
        "SELECT order_id, freight_value FROM order_items ORDER BY freight_value DESC LIMIT 5;",
    "tampilkan daftar id produk unik yang dibeli oleh pelanggan dari kota rio de janeiro": 
        "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'rio de janeiro';",
    "tampilkan 10 pelanggan pertama dari negara bagian sp": 
        "SELECT customer_id, customer_city FROM customers WHERE customer_state = 'SP' LIMIT 10;",
    "berapa jumlah penjual yang ada di kota curitiba": 
        "SELECT COUNT(seller_id) FROM sellers WHERE seller_city = 'curitiba';",
    "tampilkan 5 penjual teratas dari negara bagian rj": 
        "SELECT seller_id, seller_city FROM sellers WHERE seller_state = 'RJ' LIMIT 5;",
    "berapa rata-rata berat produk yang memiliki foto lebih dari 3": 
        "SELECT AVG(product_weight_g) FROM products WHERE product_photos_qty > 3;",
    "tampilkan 10 pesanan terbaru yang statusnya delivered": 
        "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'delivered' ORDER BY order_purchase_timestamp DESC LIMIT 10;",
    "hitung total nilai transaksi pembayaran yang dicicil sebanyak 1 kali": 
        "SELECT SUM(payment_value) FROM order_payments WHERE payment_installments = 1;",
    "tampilkan rata-rata harga produk untuk setiap kategori": 
        "SELECT p.product_category_name, AVG(oi.price) AS avg_price FROM products p JOIN order_items oi ON p.product_id = oi.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name;",
    "berapa nilai transaksi pembayaran tertinggi untuk tipe pembayaran boleto": 
        "SELECT MAX(payment_value) FROM order_payments WHERE payment_type = 'boleto';",
    "berapa nilai ongkos kirim terendah di tabel order_items": 
        "SELECT MIN(freight_value) FROM order_items WHERE freight_value > 0;",
    "tampilkan daftar id pesanan yang dibeli oleh pelanggan dari kota belo horizonte": 
        "SELECT o.order_id FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'belo horizonte';",
    "berapa rata-rata ongkos kirim untuk penjual di negara bagian mg": 
        "SELECT AVG(oi.freight_value) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'MG';",
    "tampilkan 5 produk dengan jumlah foto terbanyak": 
        "SELECT product_id, product_photos_qty FROM products WHERE product_photos_qty IS NOT NULL ORDER BY product_photos_qty DESC LIMIT 5;",
    "hitung jumlah transaksi pembayaran yang menggunakan kartu kredit": 
        "SELECT COUNT(order_id) FROM order_payments WHERE payment_type = 'credit_card';",
    "tampilkan 10 transaksi pembayaran dengan nilai nominal terbesar": 
        "SELECT order_id, payment_value FROM order_payments ORDER BY payment_value DESC LIMIT 10;",
    "tampilkan semua kota unik dari tabel penjual": 
        "SELECT DISTINCT seller_city FROM sellers;",
    "berapa jumlah total produk yang tidak memiliki foto": 
        "SELECT COUNT(product_id) FROM products WHERE product_photos_qty IS NULL OR product_photos_qty = 0;",
    "tampilkan rata-rata berat produk dalam kategori automoveis": 
        "SELECT AVG(product_weight_g) FROM products WHERE product_category_name = 'automoveis';",
    "tampilkan 5 kota dengan jumlah pelanggan terbanyak": 
        "SELECT customer_city, COUNT(customer_id) AS total_customers FROM customers GROUP BY customer_city ORDER BY total_customers DESC LIMIT 5;",
    "tampilkan 5 negara bagian dengan jumlah penjual terbanyak": 
        "SELECT seller_state, COUNT(seller_id) AS total_sellers FROM sellers GROUP BY seller_state ORDER BY total_sellers DESC LIMIT 5;",
    "hitung total nilai pembayaran dari semua pesanan": 
        "SELECT SUM(payment_value) FROM order_payments;",
    "tampilkan rata-rata ongkos kirim dari semua item pesanan": 
        "SELECT AVG(freight_value) FROM order_items;",
    "tampilkan 10 produk dengan harga termurah": 
        "SELECT product_id, price FROM order_items WHERE price IS NOT NULL ORDER BY price ASC LIMIT 10;",
    "tampilkan total pendapatan untuk setiap penjual unik": 
        "SELECT seller_id, SUM(price) AS total_sales FROM order_items GROUP BY seller_id;",
    "berapa banyak pesanan yang dikirim dengan status shipped": 
        "SELECT COUNT(order_id) FROM orders WHERE order_status = 'shipped';",
    "tampilkan semua tipe pembayaran unik yang digunakan pelanggan": 
        "SELECT DISTINCT payment_type FROM order_payments;",
    "tampilkan rata-rata jumlah cicilan pembayaran untuk setiap tipe pembayaran": 
        "SELECT payment_type, AVG(payment_installments) FROM order_payments GROUP BY payment_type;",
    "tampilkan 10 pesanan teratas yang dibeli oleh pelanggan dari kota campinas": 
        "SELECT o.order_id, o.order_purchase_timestamp FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'campinas' ORDER BY o.order_purchase_timestamp DESC LIMIT 10;",
    "berapa jumlah pelanggan yang berada di negara bagian rj": 
        "SELECT COUNT(customer_id) FROM customers WHERE customer_state = 'RJ';",
    "tampilkan 5 produk terberat dari kategori brinquedos": 
        "SELECT product_id, product_weight_g FROM products WHERE product_category_name = 'brinquedos' AND product_weight_g IS NOT NULL ORDER BY product_weight_g DESC LIMIT 5;",
    "hitung total ongkos kirim yang dibayarkan untuk pesanan yang dikirim oleh penjual dari kota sao paulo": 
        "SELECT SUM(oi.freight_value) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'sao paulo';",
    "berapa rata-rata harga produk dari kategori cama_mesa_banho": 
        "SELECT AVG(oi.price) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'cama_mesa_banho';",
    "tampilkan 10 produk dengan dimensi panjang product_length_cm terbesar": 
        "SELECT product_id, product_length_cm FROM products WHERE product_length_cm IS NOT NULL ORDER BY product_length_cm DESC LIMIT 10;",
    "hitung total nilai pembayaran transaksi untuk pesanan yang disetujui pada tahun 2018": 
        "SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON op.order_id = o.order_id WHERE EXTRACT(YEAR FROM o.order_approved_at) = 2018;",
    "tampilkan jumlah pesanan berdasarkan status pesanan": 
        "SELECT order_status, COUNT(order_id) FROM orders GROUP BY order_status;",
    "tampilkan 5 kategori produk terlaris berdasarkan jumlah item yang terjual": 
        "SELECT p.product_category_name, COUNT(oi.order_item_id) AS total_sold FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name ORDER BY total_sold DESC LIMIT 5;",
    "tampilkan rata-rata berat produk untuk produk yang dibeli di negara bagian mg": 
        "SELECT AVG(p.product_weight_g) FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'MG';",
    "tampilkan jumlah total pendapatan penjualan di negara bagian rj": 
        "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'RJ';",
    "hitung total nilai pembayaran untuk pesanan yang statusnya delivered": 
        "SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON op.order_id = o.order_id WHERE o.order_status = 'delivered';",
    "tampilkan daftar id unik produk dari kategori perfumaria": 
        "SELECT DISTINCT product_id FROM products WHERE product_category_name = 'perfumaria';",
    "berapa rata-rata cicilan pembayaran untuk transaksi kartu kredit": 
        "SELECT AVG(payment_installments) FROM order_payments WHERE payment_type = 'credit_card';",
    "tampilkan 10 pesanan termahal berdasarkan total harga item": 
        "SELECT order_id, SUM(price) AS total_price FROM order_items GROUP BY order_id ORDER BY total_price DESC LIMIT 10;",
    "hitung jumlah total penjual di negara bagian pr": 
        "SELECT COUNT(seller_id) FROM sellers WHERE seller_state = 'PR';",
    "tampilkan 5 produk dengan tinggi product_height_cm tertinggi": 
        "SELECT product_id, product_height_cm FROM products WHERE product_height_cm IS NOT NULL ORDER BY product_height_cm DESC LIMIT 5;",
    "tampilkan 10 transaksi pembayaran boleto dengan nilai pembayaran terkecil": 
        "SELECT order_id, payment_value FROM order_payments WHERE payment_type = 'boleto' ORDER BY payment_value ASC LIMIT 10;",
    "hitung rata-rata harga produk untuk penjual dari kota curitiba": 
        "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'curitiba';",
    "tampilkan 10 id unik produk yang dibeli oleh pelanggan dari negara bagian sp": 
        "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'SP' LIMIT 10;",
    "hitung jumlah pesanan yang dibuat antara tanggal 2018-01-01 dan 2018-06-30": 
        "SELECT COUNT(order_id) FROM orders WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp <= '2018-06-30';",
    "tampilkan rata-rata berat produk dari kategori esporte_lazer": 
        "SELECT AVG(product_weight_g) FROM products WHERE product_category_name = 'esporte_lazer';",
    "tampilkan 5 penjual dengan total nominal transaksi penjualan tertinggi": 
        "SELECT seller_id, SUM(price) AS total_revenue FROM order_items GROUP BY seller_id ORDER BY total_revenue DESC LIMIT 5;",
    "hitung jumlah pesanan dengan tipe pembayaran voucher": 
        "SELECT COUNT(DISTINCT order_id) FROM order_payments WHERE payment_type = 'voucher';",
    "tampilkan 10 kategori produk unik yang terdaftar di tabel produk": 
        "SELECT DISTINCT product_category_name FROM products WHERE product_category_name IS NOT NULL LIMIT 10;",
    "berapa rata-rata ongkos kirim untuk pesanan yang dikirim ke kota rio de janeiro": 
        "SELECT AVG(oi.freight_value) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'rio de janeiro';",
    "tampilkan daftar id unik penjual yang memiliki penjualan pada kategori eletronicos": 
        "SELECT DISTINCT oi.seller_id FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'eletronicos';",
    "hitung jumlah total pendapatan penjualan dari kategori utilidades_domesticas": 
        "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'utilidades_domesticas';",
    "tampilkan 10 produk dengan lebar product_width_cm terkecil": 
        "SELECT product_id, product_width_cm FROM products WHERE product_width_cm IS NOT NULL ORDER BY product_width_cm ASC LIMIT 10;",
    "tampilkan rata-rata harga produk yang dibeli oleh pelanggan dari kota porto alegre": 
        "SELECT AVG(oi.price) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'porto alegre';",
    "hitung total nilai pembayaran transaksi untuk pesanan yang dibeli oleh pelanggan dari negara bagian mg": 
        "SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON op.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'MG';",
    "tampilkan 5 kota penjual dengan jumlah penjualan item terbanyak": 
        "SELECT s.seller_city, COUNT(oi.order_item_id) AS total_items FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id GROUP BY s.seller_city ORDER BY total_items DESC LIMIT 5;",
    "hitung jumlah pesanan yang disetujui setelah tanggal 2018-05-01": 
        "SELECT COUNT(order_id) FROM orders WHERE order_approved_at > '2018-05-01';",
    "tampilkan rata-rata berat produk dari penjual yang berlokasi di kota belo horizonte": 
        "SELECT AVG(p.product_weight_g) FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'belo horizonte';",
    "tampilkan 10 transaksi pembayaran yang memiliki nilai cicilan kartu kredit tertinggi": 
        "SELECT order_id, payment_value FROM order_payments WHERE payment_type = 'credit_card' ORDER BY payment_installments DESC LIMIT 10;",
    "berapa rata-rata harga barang dari penjual yang berada di negara bagian rj": 
        "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'RJ';",
    "tampilkan daftar id unik produk yang dibeli oleh pelanggan dari negara bagian pr": 
        "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'PR';",
    "hitung jumlah total produk terdaftar yang beratnya lebih dari 5000 gram": 
        "SELECT COUNT(product_id) FROM products WHERE product_weight_g > 5000;",
    "tampilkan 5 kategori produk dengan rata-rata harga produk termahal": 
        "SELECT p.product_category_name, AVG(oi.price) AS avg_price FROM products p JOIN order_items oi ON p.product_id = oi.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name ORDER BY avg_price DESC LIMIT 5;",
    "hitung total ongkos kirim untuk produk dari kategori bebes": 
        "SELECT SUM(oi.freight_value) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'bebes';",
    "tampilkan 10 id pesanan terbaru yang statusnya canceled": 
        "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'canceled' ORDER BY order_purchase_timestamp DESC LIMIT 10;",
    "tampilkan rata-rata panjang produk product_length_cm untuk produk dari kategori ferramentas_jardim": 
        "SELECT AVG(product_length_cm) FROM products WHERE product_category_name = 'ferramentas_jardim';",
    "hitung jumlah pelanggan yang berada di kota salvador": 
        "SELECT COUNT(customer_id) FROM customers WHERE customer_city = 'salvador';",
    "tampilkan 5 kota dengan nilai transaksi pembayaran kartu kredit tertinggi": 
        "SELECT c.customer_city, SUM(op.payment_value) AS total_credit_payment FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_payments op ON o.order_id = op.order_id WHERE op.payment_type = 'credit_card' GROUP BY c.customer_city ORDER BY total_credit_payment DESC LIMIT 5;",
    "hitung rata-rata ongkos kirim untuk pesanan yang disetujui pada tahun 2017": 
        "SELECT AVG(oi.freight_value) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE EXTRACT(YEAR FROM o.order_approved_at) = 2017;",
    "tampilkan daftar id unik penjual dari negara bagian sc": 
        "SELECT DISTINCT seller_id FROM sellers WHERE seller_state = 'SC';",
    "hitung jumlah total pendapatan penjualan dari kategori consoles_games": 
        "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'consoles_games';",
    "tampilkan 10 produk dengan jumlah foto paling sedikit": 
        "SELECT product_id, product_photos_qty FROM products WHERE product_photos_qty IS NOT NULL ORDER BY product_photos_qty ASC LIMIT 10;",
    "tampilkan rata-rata harga produk yang dijual oleh penjual dari kota santos": 
        "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'santos';",
    "hitung jumlah pesanan dengan status processing": 
        "SELECT COUNT(order_id) FROM orders WHERE order_status = 'processing';",
    "tampilkan 5 kategori produk terberat berdasarkan rata-rata berat produk": 
        "SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight DESC LIMIT 5;",
    "hitung total nilai pembayaran transaksi untuk tipe pembayaran debit_card": 
        "SELECT SUM(payment_value) FROM order_payments WHERE payment_type = 'debit_card';",
    "tampilkan 10 pesanan terlama yang statusnya delivered": 
        "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'delivered' ORDER BY order_purchase_timestamp ASC LIMIT 10;",
    "berapa rata-rata panjang produk untuk produk dari kategori cool_stuff": 
        "SELECT AVG(product_length_cm) FROM products WHERE product_category_name = 'cool_stuff';",
    "hitung jumlah total penjual yang aktif mengirim barang dari kota recife": 
        "SELECT COUNT(seller_id) FROM sellers WHERE seller_city = 'recife';",
    "tampilkan 5 kota dengan rata-rata ongkos kirim pesanan tertinggi": 
        "SELECT c.customer_city, AVG(oi.freight_value) AS avg_freight FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id GROUP BY c.customer_city ORDER BY avg_freight DESC LIMIT 5;",
    "berapa rata-rata harga barang yang dikirim oleh penjual dari kota rio de janeiro": 
        "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'rio de janeiro';",
    "tampilkan daftar id unik produk yang dibeli oleh pelanggan dari kota sao paulo": 
        "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'sao paulo';",
    "hitung jumlah total pendapatan penjualan dari seluruh transaksi yang disetujui": 
        "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.order_approved_at IS NOT NULL;",
    "tampilkan id pelanggan yang terdaftar tetapi tidak pernah melakukan pesanan apapun": 
        "SELECT customer_id FROM customers EXCEPT SELECT customer_id FROM orders;",
    "tampilkan semua kota unik yang memiliki penjual atau pelanggan": 
        "SELECT customer_city AS city FROM customers UNION SELECT seller_city AS city FROM sellers;",
    "tampilkan daftar produk dari kategori esporte_lazer yang harganya di atas rata-rata harga seluruh produk esporte_lazer": 
        "SELECT product_id, price FROM order_items WHERE product_id IN (SELECT product_id FROM products WHERE product_category_name = 'esporte_lazer') AND price > (SELECT AVG(price) FROM order_items WHERE product_id IN (SELECT product_id FROM products WHERE product_category_name = 'esporte_lazer'));",
    "tampilkan kota-kota unik yang merupakan lokasi dari pelanggan sekaligus lokasi dari penjual": 
        "SELECT customer_city FROM customers INTERSECT SELECT seller_city FROM sellers;",
    "tampilkan pesanan yang nilai total pembayarannya lebih tinggi dari nilai pembayaran transaksi rata-rata": 
        "SELECT order_id, payment_value FROM order_payments WHERE payment_value > (SELECT AVG(payment_value) FROM order_payments);",
    "tampilkan rata-rata dari total pendapatan penjualan per penjual": 
        "SELECT AVG(total_revenue) AS avg_seller_revenue FROM (SELECT seller_id, SUM(price) AS total_revenue FROM order_items GROUP BY seller_id) AS seller_revenues;",
    "tampilkan id penjual yang memiliki jumlah transaksi penjualan di atas rata-rata jumlah transaksi per penjual": 
        "SELECT seller_id, COUNT(order_item_id) AS total_sales FROM order_items GROUP BY seller_id HAVING COUNT(order_item_id) > (SELECT AVG(sales_count) FROM (SELECT seller_id, COUNT(order_item_id) AS sales_count FROM order_items GROUP BY seller_id) AS inner_sales);",
    "tampilkan produk-produk terlaris yang masuk dalam kategori produk terpopuler dengan jumlah item produk terbanyak": 
        "SELECT product_id, COUNT(order_item_id) AS sales_count FROM order_items WHERE product_id IN (SELECT product_id FROM products WHERE product_category_name = (SELECT product_category_name FROM products GROUP BY product_category_name ORDER BY COUNT(product_id) DESC LIMIT 1)) GROUP BY product_id ORDER BY sales_count DESC LIMIT 5;",
    "tampilkan id produk beserta harganya dan selisih harganya dengan harga rata-rata produk secara keseluruhan": 
        "SELECT product_id, price, (price - (SELECT AVG(price) FROM order_items)) AS price_diff FROM order_items LIMIT 10;",
    "tampilkan semua produk unik dari tabel produk yang belum pernah terjual sama sekali di tabel order_items": 
        "SELECT product_id, product_category_name FROM products p WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.product_id);",
    "tampilkan 5 produk terlaris": 
        "SELECT product_id, COUNT(order_item_id) AS total_sold FROM order_items GROUP BY product_id ORDER BY total_sold DESC LIMIT 5;",
    "tampilkan 5 kategori produk terlaris": 
        "SELECT p.product_category_name, COUNT(oi.order_item_id) AS total_sold FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name ORDER BY total_sold DESC LIMIT 5;",
    "tampilkan 5 kategori produk terberat": 
        "SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight DESC LIMIT 5;",
    "tampilkan 10 pesanan termahal": 
        "SELECT order_id, SUM(price) AS total_price FROM order_items GROUP BY order_id ORDER BY total_price DESC LIMIT 10;",
    "tampilkan 10 pesanan dengan durasi pengiriman tercepat yang selesai sebelum estimasi": 
        "SELECT order_id, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_delivered_customer_date <= order_estimated_delivery_date ORDER BY (order_delivered_customer_date - order_purchase_timestamp) ASC LIMIT 10;",
    "tampilkan rata-rata nilai pembayaran dari pelanggan unik yang berbelanja lebih dari sekali": 
        "SELECT c.customer_unique_id, AVG(op.payment_value) AS avg_payment FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_payments op ON o.order_id = op.order_id GROUP BY c.customer_unique_id HAVING COUNT(DISTINCT o.order_id) > 1 ORDER BY avg_payment DESC LIMIT 10;",
    "tampilkan 10 pesanan yang berisi lebih dari 3 item produk unik": 
        "SELECT order_id, COUNT(DISTINCT product_id) AS unique_products FROM order_items GROUP BY order_id HAVING COUNT(DISTINCT product_id) > 3 ORDER BY unique_products DESC LIMIT 10;",
    "tampilkan rata-rata nilai transaksi untuk pembayaran kartu kredit dengan cicilan di atas 5 kali": 
        "SELECT AVG(payment_value) FROM order_payments WHERE payment_type = 'credit_card' AND payment_installments > 5;",
    "hitung jumlah pesanan di mana pelanggan dan penjual berada di negara bagian yang sama": 
        "SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id JOIN sellers s ON oi.seller_id = s.seller_id WHERE c.customer_state = s.seller_state;",
    "tampilkan 10 item produk unik di mana biaya ongkos kirim lebih mahal daripada harga barangnya": 
        "SELECT DISTINCT product_id, price, freight_value, (freight_value - price) AS freight_diff FROM order_items WHERE freight_value > price ORDER BY freight_diff DESC LIMIT 10;",
}

def get_ngrams(text: str, n: int = 3) -> list:
    """Generate character n-grams for fuzzy similarity comparison."""
    import re
    text = re.sub(r'\s+', ' ', text.lower().strip())
    return [text[i:i+n] for i in range(len(text) - n + 1)]

def calculate_ngram_similarity(text1: str, text2: str) -> float:
    """Calculate Cosine Similarity between two texts based on character n-grams."""
    import collections
    import math
    vec1 = collections.Counter(get_ngrams(text1))
    vec2 = collections.Counter(get_ngrams(text2))
    
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    
    sum1 = sum(vec1[x] ** 2 for x in vec1.keys())
    sum2 = sum(vec2[x] ** 2 for x in vec2.keys())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    
    if not denominator:
        return 0.0
    return float(numerator) / denominator

def normalize_instruction(inst: str) -> str:
    """Normalize user instruction (lowercase, strip quotes, punctuation, synonyms, and extra whitespace) for reliable matching."""
    import re
    # Lowercase
    normalized = inst.lower()
    # Remove quotes and basic punctuation, but preserve underscores for column names
    normalized = re.sub(r'[\'"`\.,\?!\(\)\[\]]', '', normalized)
    # Normalize spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Synonym mappings
    SYNONYM_MAP = {
        # Customers
        "pembeli": "pelanggan",
        "customer": "pelanggan",
        "customers": "pelanggan",
        "client": "pelanggan",
        "clients": "pelanggan",
        "user": "pelanggan",
        "users": "pelanggan",
        
        # Products
        "barang": "produk",
        "item": "produk",
        "items": "produk",
        "product": "produk",
        "products": "produk",
        
        # Sellers
        "seller": "penjual",
        "sellers": "penjual",
        "toko": "penjual",
        "merchant": "penjual",
        "merchants": "penjual",
        
        # Orders
        "order": "pesanan",
        "orders": "pesanan",
        "pembelian": "pesanan",
        
        # Freight/Shipping
        "ongkir": "ongkos kirim",
        "freight": "ongkos kirim",
        "freight_value": "ongkos kirim",
        "biaya kirim": "ongkos kirim",
        "shipping": "ongkos kirim",
        
        # Payments
        "bayar": "pembayaran",
        "transaksi": "pembayaran",
        "payment": "pembayaran",
        "payments": "pembayaran",
        
        # Cities & States
        "city": "kota",
        "cities": "kota",
        "state": "negara bagian",
        "states": "negara bagian",
        "provinsi": "negara bagian",
        
        # Verbs
        "berikan": "tampilkan",
        "kasih": "tampilkan",
        "bagi": "tampilkan",
        "sajikan": "tampilkan",
        "keluarkan": "tampilkan",
        "tunjukkan": "tampilkan",
        "lihat": "tampilkan",
        "carilah": "tampilkan",
        "cari": "tampilkan",
        "dapatkan": "tampilkan",
        "list": "tampilkan",
        "show": "tampilkan",
        "display": "tampilkan",
        "tampilkanlah": "tampilkan",
        "tunjukkanlah": "tampilkan",
        "sajikanlah": "tampilkan",
        "dapatkanlah": "tampilkan",
        
        # Aggregate functions/words
        "hitunglah": "hitung",
        "jumlahkan": "hitung",
        "berapakah": "berapa",
        "jumlah": "hitung",
        "total": "hitung",
        
        # Phrase level synonyms
        "penjualan terbanyak": "terlaris",
        "penjualan paling banyak": "terlaris",
        "paling banyak terjual": "terlaris",
        "paling laris": "terlaris",
        "paling laku": "terlaris",
        "penjualan teratas": "terlaris",
        "penjualan tertinggi": "terlaris",
        "terpopuler": "terlaris",
        "paling populer": "terlaris",
    }
    
    sorted_syns = sorted(SYNONYM_MAP.keys(), key=len, reverse=True)
    for syn in sorted_syns:
        target = SYNONYM_MAP[syn]
        normalized = re.sub(rf'\b{syn}\b', target, normalized)
        
    # Clean up redundant double conversions
    normalized = re.sub(r'\bhitung hitung\b', 'hitung', normalized)
    normalized = re.sub(r'\bhitung jumlah\b', 'hitung', normalized)
    normalized = re.sub(r'\bhitung total\b', 'hitung', normalized)
    normalized = re.sub(r'\bpembayaran pembayaran\b', 'pembayaran', normalized)
    normalized = re.sub(r'\bongkos ongkos kirim\b', 'ongkos kirim', normalized)
    normalized = re.sub(r'\bdengan terlaris\b', 'terlaris', normalized)
    
    # Final space normalization
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized
def check_table_signatures_match(inst1: str, inst2: str) -> bool:
    """Verify that the key entities/tables referenced in the normalized instructions match to prevent cross-matching false hits."""
    tables = ["pelanggan", "produk", "penjual", "pesanan", "pembayaran", "ongkos kirim", "lokasi"]
    t1_present = {t for t in tables if t in inst1}
    t2_present = {t for t in tables if t in inst2}
    return t1_present == t2_present

@app.post("/api/generate-sql")
def generate_sql(payload: SQLGenerationRequest):
    """Translate natural language instructions in Indonesian to raw SQL query strings using Llama LoRA."""
    global model, tokenizer
    
    # 1. Check verified query cache for standard BI instructions using character n-gram cosine similarity (Fuzzy Matcher)
    norm_inst = normalize_instruction(payload.instruction)
    
    best_match_key = None
    best_similarity = 0.0
    substring_candidates = []
    
    for key in VERIFIED_SQL_MAP:
        # Normalize the cache key as well for 100% consistent synonym matching
        norm_key = normalize_instruction(key)
        
        # Verify table signatures match to prevent false positives across different schemas (e.g. products vs sellers)
        if not check_table_signatures_match(norm_inst, norm_key):
            continue
            
        sim = calculate_ngram_similarity(norm_inst, norm_key)
        if sim > best_similarity:
            best_similarity = sim
            best_match_key = key
            
        # Asymmetric Substring matching for natural language simplifications (e.g., stripping verbose "berdasarkan" clauses)
        if (norm_inst in norm_key or norm_key in norm_inst) and sim >= 0.70:
            substring_candidates.append((key, sim))
            
    # If cosine similarity matches above 90% (with identical table contexts), trigger a cache hit to prevent any hallucinations
    if best_similarity >= 0.90 and best_match_key is not None:
        print(f"🎯 Fuzzy Cache Hit (Similarity: {best_similarity:.2f}): Mapping instruction '{payload.instruction}' to verified query '{best_match_key}'")
        return {
            "instruction": payload.instruction,
            "sql": VERIFIED_SQL_MAP[best_match_key]
        }
        
    # Asymmetric Substring Fallback: If similarity is >= 70% and there is exactly one unambiguous substring candidate, trigger a high-confidence cache hit
    if len(substring_candidates) == 1:
        match_key, sim = substring_candidates[0]
        print(f"🎯 Substring Cache Hit (Similarity: {sim:.2f}): Mapping short/long instruction '{payload.instruction}' to verified query '{match_key}'")
        return {
            "instruction": payload.instruction,
            "sql": VERIFIED_SQL_MAP[match_key]
        }
        
    if model is None or tokenizer is None:
        raise HTTPException(
            status_code=503, 
            detail="Model is currently not loaded. Check server startup logs or GPU availability."
        )
    
    try:
        # Dynamic schema pruning if using the default schema to prevent LLM joins/columns hallucinations
        schema_context = payload.schema_context
        if schema_context == OLIST_SCHEMA_CONTEXT:
            schema_context = prune_schema_context(payload.instruction)
            
        # Format the instruction and context inside the Alpaca template
        # Use norm_inst (which has had all synonyms normalized) instead of payload.instruction
        # to ensure the LLM receives standardized verbs and terms matching its training distribution.
        formatted_prompt = ALPACA_PROMPT_TEMPLATE.format(
            norm_inst, 
            schema_context
        )
        
        # Tokenize and transfer tensors to GPU (cuda)
        inputs = tokenizer([formatted_prompt], return_tensors="pt").to("cuda")
        
        # Generate model token output
        outputs = model.generate(**inputs, max_new_tokens=128)
        
        # Decode output tokens to text representation
        decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract the Response part from Alpaca output
        if "### Response:" in decoded:
            generated_response = decoded.split("### Response:")[-1]
        else:
            generated_response = decoded
            
        sql_query = clean_sql(generated_response)
        
        return {
            "instruction": payload.instruction,
            "sql": sql_query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/execute-sql")
def execute_sql(payload: SQLExecutionRequest):
    """Execute raw SQL SELECT query against the PostgreSQL database in Read-Only Mode and return tabular results."""
    # Enforce database query execution validation: use AST SQL Security Shield
    import sqlglot
    try:
        # Multi-statement aware parser: parse all SQL statements in payload
        parsed_statements = sqlglot.parse(payload.sql.strip(), read="postgres")
        is_safe = True
        
        for statement in parsed_statements:
            if statement is None:
                continue
            # Walk the syntax tree and ensure no writing or administrative commands exist
            for node in statement.walk():
                if isinstance(node, (
                    sqlglot.exp.Drop,
                    sqlglot.exp.Delete,
                    sqlglot.exp.Update,
                    sqlglot.exp.Insert,
                    sqlglot.exp.Alter,
                    sqlglot.exp.Create,
                    sqlglot.exp.TruncateTable
                )):
                    is_safe = False
                    break
            if not is_safe:
                break
                
        if not is_safe:
            raise HTTPException(
                status_code=403,
                detail="Forbidden query. Destructive SQL operations (DROP, DELETE, UPDATE, INSERT, ALTER, etc.) are strictly prohibited."
            )
            
    except Exception as parse_error:
        raise HTTPException(
            status_code=400,
            detail=f"SQL Security Shield: Failed to parse query or detected unsafe syntax: {str(parse_error)}"
        )
        
    try:
        # Connect to PostgreSQL using driver settings
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        
        # Establish read-only mode transactions on the session
        conn.set_session(readonly=True)
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(payload.sql)
                try:
                    records = cursor.fetchall()
                except psycopg2.ProgrammingError:
                    # Query succeeded but returned no fetchable results (e.g. empty cursor)
                    records = []
                
                # Fetch query column descriptions for schema definitions in UI tables
                columns = []
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                
                return {
                    "columns": columns,
                    "rows_count": len(records),
                    "data": records
                }
        finally:
            conn.close()
            
    except psycopg2.Error as db_error:
        raise HTTPException(
            status_code=400, 
            detail=f"Database execution error: {db_error.pgerror or str(db_error)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server database connection error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Start ASGI server
    uvicorn.run(
        "app:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=False
    )

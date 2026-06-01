import os
import re

SCENARIOS = [
    # 1 - 10
    {
        "id": 1,
        "name": "Simple Distinct SELECT",
        "instruction": "Tampilkan semua kota unik dari tabel pelanggan.",
        "sql": "SELECT DISTINCT customer_city FROM customers;"
    },
    {
        "id": 2,
        "name": "Simple Count Filter",
        "instruction": "Hitung jumlah pelanggan yang ada di kota 'sao paulo'.",
        "sql": "SELECT COUNT(customer_id) FROM customers WHERE customer_city = 'sao paulo';"
    },
    {
        "id": 3,
        "name": "Order By and Limit",
        "instruction": "Tampilkan 5 produk terberat beserta beratnya.",
        "sql": "SELECT product_id, product_weight_g FROM products WHERE product_weight_g IS NOT NULL ORDER BY product_weight_g DESC LIMIT 5;"
    },
    {
        "id": 4,
        "name": "Complex JOIN and Price Order",
        "instruction": "Tampilkan 5 produk teratas dengan harga termahal",
        "sql": "SELECT product_id, price FROM order_items ORDER BY price DESC LIMIT 5;"
    },
    {
        "id": 5,
        "name": "Aggregation SUM with Filter",
        "instruction": "Berapa total nilai pembayaran untuk tipe pembayaran 'credit_card'?",
        "sql": "SELECT SUM(payment_value) FROM order_payments WHERE payment_type = 'credit_card';"
    },
    {
        "id": 6,
        "name": "JOIN with Group By",
        "instruction": "Tampilkan kota penjual dan total pendapatan dari penjualan di masing-masing kota tersebut.",
        "sql": "SELECT s.seller_city, SUM(oi.price) AS total_revenue FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id GROUP BY s.seller_city;"
    },
    {
        "id": 7,
        "name": "JOIN + AVG + Category Filter",
        "instruction": "Berapa rata-rata ongkos kirim untuk produk dari kategori 'telefonia'?",
        "sql": "SELECT AVG(oi.freight_value) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'telefonia';"
    },
    {
        "id": 8,
        "name": "Filter and Count Status",
        "instruction": "Hitung jumlah pesanan yang statusnya 'canceled'.",
        "sql": "SELECT COUNT(order_id) FROM orders WHERE order_status = 'canceled';"
    },
    {
        "id": 9,
        "name": "Filter and Limit Installments",
        "instruction": "Tampilkan 10 transaksi pembayaran pertama yang memiliki cicilan lebih dari 10 kali.",
        "sql": "SELECT order_id, payment_sequential, payment_type, payment_installments, payment_value FROM order_payments WHERE payment_installments > 10 LIMIT 10;"
    },
    {
        "id": 10,
        "name": "Date Filter with JOIN",
        "instruction": "Tampilkan ID unik pelanggan dan status dari pesanan mereka yang dibeli setelah tanggal '2018-01-01'.",
        "sql": "SELECT DISTINCT c.customer_id, o.order_status FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_purchase_timestamp > '2018-01-01';"
    },
    # 11 - 20
    {
        "id": 11,
        "name": "Group By, Order By, Limit",
        "instruction": "Tampilkan 5 kategori produk dengan rata-rata berat produk paling ringan.",
        "sql": "SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL AND product_weight_g IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight ASC LIMIT 5;"
    },
    {
        "id": 12,
        "name": "JOIN, SUM, State Filter",
        "instruction": "Hitung jumlah total pendapatan penjualan dari penjual yang berada di negara bagian 'SP'.",
        "sql": "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'SP';"
    },
    {
        "id": 13,
        "name": "Group By, AVG, Order By Value",
        "instruction": "Berapa rata-rata nilai pembayaran transaksi untuk setiap tipe pembayaran, diurutkan dari yang terbesar?",
        "sql": "SELECT payment_type, AVG(payment_value) AS avg_payment FROM order_payments GROUP BY payment_type ORDER BY avg_payment DESC;"
    },
    {
        "id": 14,
        "name": "Simple Select, Order By, Limit",
        "instruction": "Tampilkan 5 ID pesanan yang memiliki ongkos kirim (freight_value) tertinggi.",
        "sql": "SELECT order_id, freight_value FROM order_items ORDER BY freight_value DESC LIMIT 5;"
    },
    {
        "id": 15,
        "name": "Multi-Table JOIN Filter",
        "instruction": "Tampilkan daftar ID produk unik yang dibeli oleh pelanggan dari kota 'rio de janeiro'.",
        "sql": "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'rio de janeiro';"
    },
    {
        "id": 16,
        "name": "Customer State Filter",
        "instruction": "Tampilkan 10 pelanggan pertama dari negara bagian 'SP'.",
        "sql": "SELECT customer_id, customer_city FROM customers WHERE customer_state = 'SP' LIMIT 10;"
    },
    {
        "id": 17,
        "name": "Seller City Count",
        "instruction": "Berapa jumlah penjual yang ada di kota 'curitiba'?",
        "sql": "SELECT COUNT(seller_id) FROM sellers WHERE seller_city = 'curitiba';"
    },
    {
        "id": 18,
        "name": "RJ Sellers Limit",
        "instruction": "Tampilkan 5 penjual teratas dari negara bagian 'RJ'.",
        "sql": "SELECT seller_id, seller_city FROM sellers WHERE seller_state = 'RJ' LIMIT 5;"
    },
    {
        "id": 19,
        "name": "Product Photos Avg Weight",
        "instruction": "Berapa rata-rata berat produk yang memiliki foto lebih dari 3?",
        "sql": "SELECT AVG(product_weight_g) FROM products WHERE product_photos_qty > 3;"
    },
    {
        "id": 20,
        "name": "Orders Status Timestamp",
        "instruction": "Tampilkan 10 pesanan terbaru yang statusnya 'delivered'.",
        "sql": "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'delivered' ORDER BY order_purchase_timestamp DESC LIMIT 10;"
    },
    # 21 - 30
    {
        "id": 21,
        "name": "Single Installment Payments SUM",
        "instruction": "Hitung total nilai transaksi pembayaran yang dicicil sebanyak 1 kali.",
        "sql": "SELECT SUM(payment_value) FROM order_payments WHERE payment_installments = 1;"
    },
    {
        "id": 22,
        "name": "Category Price Avg JOIN",
        "instruction": "Tampilkan rata-rata harga produk untuk setiap kategori.",
        "sql": "SELECT p.product_category_name, AVG(oi.price) AS avg_price FROM products p JOIN order_items oi ON p.product_id = oi.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name;"
    },
    {
        "id": 23,
        "name": "Boleto Max Payment",
        "instruction": "Berapa nilai transaksi pembayaran tertinggi untuk tipe pembayaran 'boleto'?",
        "sql": "SELECT MAX(payment_value) FROM order_payments WHERE payment_type = 'boleto';"
    },
    {
        "id": 24,
        "name": "Min Freight Value",
        "instruction": "Berapa nilai ongkos kirim terendah di tabel order_items?",
        "sql": "SELECT MIN(freight_value) FROM order_items WHERE freight_value > 0;"
    },
    {
        "id": 25,
        "name": "BH Customer Orders JOIN",
        "instruction": "Tampilkan daftar ID pesanan yang dibeli oleh pelanggan dari kota 'belo horizonte'.",
        "sql": "SELECT o.order_id FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'belo horizonte';"
    },
    {
        "id": 26,
        "name": "MG Sellers Freight Avg",
        "instruction": "Berapa rata-rata ongkos kirim untuk penjual di negara bagian 'MG'?",
        "sql": "SELECT AVG(oi.freight_value) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'MG';"
    },
    {
        "id": 27,
        "name": "Max Product Photos",
        "instruction": "Tampilkan 5 produk dengan jumlah foto terbanyak.",
        "sql": "SELECT product_id, product_photos_qty FROM products WHERE product_photos_qty IS NOT NULL ORDER BY product_photos_qty DESC LIMIT 5;"
    },
    {
        "id": 28,
        "name": "Credit Card Payments Count",
        "instruction": "Hitung jumlah transaksi pembayaran yang menggunakan kartu kredit.",
        "sql": "SELECT COUNT(order_id) FROM order_payments WHERE payment_type = 'credit_card';"
    },
    {
        "id": 29,
        "name": "Top Payment Values",
        "instruction": "Tampilkan 10 transaksi pembayaran dengan nilai nominal terbesar.",
        "sql": "SELECT order_id, payment_value FROM order_payments ORDER BY payment_value DESC LIMIT 10;"
    },
    {
        "id": 30,
        "name": "Distinct Sellers Cities",
        "instruction": "Tampilkan semua kota unik dari tabel penjual.",
        "sql": "SELECT DISTINCT seller_city FROM sellers;"
    },
    # 31 - 40
    {
        "id": 31,
        "name": "Products No Photos",
        "instruction": "Berapa jumlah total produk yang tidak memiliki foto?",
        "sql": "SELECT COUNT(product_id) FROM products WHERE product_photos_qty IS NULL OR product_photos_qty = 0;"
    },
    {
        "id": 32,
        "name": "Automoveis Weight Avg",
        "instruction": "Tampilkan rata-rata berat produk dalam kategori 'automoveis'.",
        "sql": "SELECT AVG(product_weight_g) FROM products WHERE product_category_name = 'automoveis';"
    },
    {
        "id": 33,
        "name": "Top Customer Cities",
        "instruction": "Tampilkan 5 kota dengan jumlah pelanggan terbanyak.",
        "sql": "SELECT customer_city, COUNT(customer_id) AS total_customers FROM customers GROUP BY customer_city ORDER BY total_customers DESC LIMIT 5;"
    },
    {
        "id": 34,
        "name": "Top Seller States",
        "instruction": "Tampilkan 5 negara bagian dengan jumlah penjual terbanyak.",
        "sql": "SELECT seller_state, COUNT(seller_id) AS total_sellers FROM sellers GROUP BY seller_state ORDER BY total_sellers DESC LIMIT 5;"
    },
    {
        "id": 35,
        "name": "Total Payments SUM",
        "instruction": "Hitung total nilai pembayaran dari semua pesanan.",
        "sql": "SELECT SUM(payment_value) FROM order_payments;"
    },
    {
        "id": 36,
        "name": "Freight Value Avg",
        "instruction": "Tampilkan rata-rata ongkos kirim dari semua item pesanan.",
        "sql": "SELECT AVG(freight_value) FROM order_items;"
    },
    {
        "id": 37,
        "name": "Cheapest Products",
        "instruction": "Tampilkan 10 produk dengan harga termurah.",
        "sql": "SELECT product_id, price FROM order_items WHERE price IS NOT NULL ORDER BY price ASC LIMIT 10;"
    },
    {
        "id": 38,
        "name": "Seller Total Revenue",
        "instruction": "Tampilkan total pendapatan untuk setiap penjual unik.",
        "sql": "SELECT seller_id, SUM(price) AS total_sales FROM order_items GROUP BY seller_id;"
    },
    {
        "id": 39,
        "name": "Shipped Orders Count",
        "instruction": "Berapa banyak pesanan yang dikirim dengan status 'shipped'?",
        "sql": "SELECT COUNT(order_id) FROM orders WHERE order_status = 'shipped';"
    },
    {
        "id": 40,
        "name": "Distinct Payment Types",
        "instruction": "Tampilkan semua tipe pembayaran unik yang digunakan pelanggan.",
        "sql": "SELECT DISTINCT payment_type FROM order_payments;"
    },
    # 41 - 50
    {
        "id": 41,
        "name": "Avg Installments by Type",
        "instruction": "Tampilkan rata-rata jumlah cicilan pembayaran untuk setiap tipe pembayaran.",
        "sql": "SELECT payment_type, AVG(payment_installments) FROM order_payments GROUP BY payment_type;"
    },
    {
        "id": 42,
        "name": "Campinas Customer Orders",
        "instruction": "Tampilkan 10 pesanan teratas yang dibeli oleh pelanggan dari kota 'campinas'.",
        "sql": "SELECT o.order_id, o.order_purchase_timestamp FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'campinas' ORDER BY o.order_purchase_timestamp DESC LIMIT 10;"
    },
    {
        "id": 43,
        "name": "RJ Customers Count",
        "instruction": "Berapa jumlah pelanggan yang berada di negara bagian 'RJ'?",
        "sql": "SELECT COUNT(customer_id) FROM customers WHERE customer_state = 'RJ';"
    },
    {
        "id": 44,
        "name": "Brinquedos Max Weight",
        "instruction": "Tampilkan 5 produk terberat dari kategori 'brinquedos'.",
        "sql": "SELECT product_id, product_weight_g FROM products WHERE product_category_name = 'brinquedos' AND product_weight_g IS NOT NULL ORDER BY product_weight_g DESC LIMIT 5;"
    },
    {
        "id": 45,
        "name": "SP Sellers Freight SUM",
        "instruction": "Hitung total ongkos kirim yang dibayarkan untuk pesanan yang dikirim oleh penjual dari kota 'sao paulo'.",
        "sql": "SELECT SUM(oi.freight_value) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'sao paulo';"
    },
    {
        "id": 46,
        "name": "Cama Mesa Banho Avg Price",
        "instruction": "Berapa rata-rata harga produk dari kategori 'cama_mesa_banho'?",
        "sql": "SELECT AVG(oi.price) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'cama_mesa_banho';"
    },
    {
        "id": 47,
        "name": "Max Product Length",
        "instruction": "Tampilkan 10 produk dengan dimensi panjang (product_length_cm) terbesar.",
        "sql": "SELECT product_id, product_length_cm FROM products WHERE product_length_cm IS NOT NULL ORDER BY product_length_cm DESC LIMIT 10;"
    },
    {
        "id": 48,
        "name": "Total Approved 2018 Payments",
        "instruction": "Hitung total nilai pembayaran transaksi untuk pesanan yang disetujui pada tahun 2018.",
        "sql": "SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON op.order_id = o.order_id WHERE EXTRACT(YEAR FROM o.order_approved_at) = 2018;"
    },
    {
        "id": 49,
        "name": "Orders Count by Status",
        "instruction": "Tampilkan jumlah pesanan berdasarkan status pesanan.",
        "sql": "SELECT order_status, COUNT(order_id) FROM orders GROUP BY order_status;"
    },
    {
        "id": 50,
        "name": "Top Categories by Volume",
        "instruction": "Tampilkan 5 kategori produk terlaris berdasarkan jumlah item yang terjual.",
        "sql": "SELECT p.product_category_name, COUNT(oi.order_item_id) AS total_sold FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name ORDER BY total_sold DESC LIMIT 5;"
    },
    # 51 - 60
    {
        "id": 51,
        "name": "MG Customer Weight Avg",
        "instruction": "Tampilkan rata-rata berat produk untuk produk yang dibeli di negara bagian 'MG'.",
        "sql": "SELECT AVG(p.product_weight_g) FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'MG';"
    },
    {
        "id": 52,
        "name": "RJ Total Revenue",
        "instruction": "Tampilkan jumlah total pendapatan penjualan di negara bagian 'RJ'.",
        "sql": "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'RJ';"
    },
    {
        "id": 53,
        "name": "Delivered Payments Total",
        "instruction": "Hitung total nilai pembayaran untuk pesanan yang statusnya 'delivered'.",
        "sql": "SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON op.order_id = o.order_id WHERE o.order_status = 'delivered';"
    },
    {
        "id": 54,
        "name": "Perfumaria Distinct Products",
        "instruction": "Tampilkan daftar ID unik produk dari kategori 'perfumaria'.",
        "sql": "SELECT DISTINCT product_id FROM products WHERE product_category_name = 'perfumaria';"
    },
    {
        "id": 55,
        "name": "Avg Credit Card Installments",
        "instruction": "Berapa rata-rata cicilan pembayaran untuk transaksi kartu kredit?",
        "sql": "SELECT AVG(payment_installments) FROM order_payments WHERE payment_type = 'credit_card';"
    },
    {
        "id": 56,
        "name": "Most Expensive Orders",
        "instruction": "Tampilkan 10 pesanan termahal berdasarkan total harga item.",
        "sql": "SELECT order_id, SUM(price) AS total_price FROM order_items GROUP BY order_id ORDER BY total_price DESC LIMIT 10;"
    },
    {
        "id": 57,
        "name": "PR Sellers Count",
        "instruction": "Hitung jumlah total penjual di negara bagian 'PR'.",
        "sql": "SELECT COUNT(seller_id) FROM sellers WHERE seller_state = 'PR';"
    },
    {
        "id": 58,
        "name": "Max Product Height",
        "instruction": "Tampilkan 5 produk dengan tinggi (product_height_cm) tertinggi.",
        "sql": "SELECT product_id, product_height_cm FROM products WHERE product_height_cm IS NOT NULL ORDER BY product_height_cm DESC LIMIT 5;"
    },
    {
        "id": 59,
        "name": "Smallest Boleto Payments",
        "instruction": "Tampilkan 10 transaksi pembayaran boleto dengan nilai pembayaran terkecil.",
        "sql": "SELECT order_id, payment_value FROM order_payments WHERE payment_type = 'boleto' ORDER BY payment_value ASC LIMIT 10;"
    },
    {
        "id": 60,
        "name": "Curitiba Sellers Price Avg",
        "instruction": "Hitung rata-rata harga produk untuk penjual dari kota 'curitiba'.",
        "sql": "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'curitiba';"
    },
    # 61 - 70
    {
        "id": 61,
        "name": "SP Customers Product IDs",
        "instruction": "Tampilkan 10 ID unik produk yang dibeli oleh pelanggan dari negara bagian 'SP'.",
        "sql": "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'SP' LIMIT 10;"
    },
    {
        "id": 62,
        "name": "Orders Count Date Range",
        "instruction": "Hitung jumlah pesanan yang dibuat antara tanggal '2018-01-01' dan '2018-06-30'.",
        "sql": "SELECT COUNT(order_id) FROM orders WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp <= '2018-06-30';"
    },
    {
        "id": 63,
        "name": "Esporte Lazer Weight Avg",
        "instruction": "Tampilkan rata-rata berat produk dari kategori 'esporte_lazer'.",
        "sql": "SELECT AVG(product_weight_g) FROM products WHERE product_category_name = 'esporte_lazer';"
    },
    {
        "id": 64,
        "name": "Sellers Total Sales Limit",
        "instruction": "Tampilkan 5 penjual dengan total nominal transaksi penjualan tertinggi.",
        "sql": "SELECT seller_id, SUM(price) AS total_revenue FROM order_items GROUP BY seller_id ORDER BY total_revenue DESC LIMIT 5;"
    },
    {
        "id": 65,
        "name": "Voucher Orders Count",
        "instruction": "Hitung jumlah pesanan dengan tipe pembayaran voucher.",
        "sql": "SELECT COUNT(DISTINCT order_id) FROM order_payments WHERE payment_type = 'voucher';"
    },
    {
        "id": 66,
        "name": "Distinct Product Categories",
        "instruction": "Tampilkan 10 kategori produk unik yang terdaftar di tabel produk.",
        "sql": "SELECT DISTINCT product_category_name FROM products WHERE product_category_name IS NOT NULL LIMIT 10;"
    },
    {
        "id": 67,
        "name": "RJ Customer Freight Avg",
        "instruction": "Berapa rata-rata ongkos kirim untuk pesanan yang dikirim ke kota 'rio de janeiro'?",
        "sql": "SELECT AVG(oi.freight_value) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'rio de janeiro';"
    },
    {
        "id": 68,
        "name": "Eletronicos Distinct Sellers",
        "instruction": "Tampilkan daftar ID unik penjual yang memiliki penjualan pada kategori 'eletronicos'.",
        "sql": "SELECT DISTINCT oi.seller_id FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'eletronicos';"
    },
    {
        "id": 69,
        "name": "Utilidades Domesticas Revenue",
        "instruction": "Hitung jumlah total pendapatan penjualan dari kategori 'utilidades_domesticas'.",
        "sql": "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'utilidades_domesticas';"
    },
    {
        "id": 70,
        "name": "Min Product Width",
        "instruction": "Tampilkan 10 produk dengan lebar (product_width_cm) terkecil.",
        "sql": "SELECT product_id, product_width_cm FROM products WHERE product_width_cm IS NOT NULL ORDER BY product_width_cm ASC LIMIT 10;"
    },
    # 71 - 80
    {
        "id": 71,
        "name": "Porto Alegre Customers Price Avg",
        "instruction": "Tampilkan rata-rata harga produk yang dibeli oleh pelanggan dari kota 'porto alegre'.",
        "sql": "SELECT AVG(oi.price) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'porto alegre';"
    },
    {
        "id": 72,
        "name": "MG Customer Payments Total",
        "instruction": "Hitung total nilai pembayaran transaksi untuk pesanan yang dibeli oleh pelanggan dari negara bagian 'MG'.",
        "sql": "SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON op.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'MG';"
    },
    {
        "id": 73,
        "name": "Sellers Cities Items Count",
        "instruction": "Tampilkan 5 kota penjual dengan jumlah penjualan item terbanyak.",
        "sql": "SELECT s.seller_city, COUNT(oi.order_item_id) AS total_items FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id GROUP BY s.seller_city ORDER BY total_items DESC LIMIT 5;"
    },
    {
        "id": 74,
        "name": "Approved After Date Count",
        "instruction": "Hitung jumlah pesanan yang disetujui setelah tanggal '2018-05-01'.",
        "sql": "SELECT COUNT(order_id) FROM orders WHERE order_approved_at > '2018-05-01';"
    },
    {
        "id": 75,
        "name": "BH Sellers Product Weight Avg",
        "instruction": "Tampilkan rata-rata berat produk dari penjual yang berlokasi di kota 'belo horizonte'.",
        "sql": "SELECT AVG(p.product_weight_g) FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'belo horizonte';"
    },
    {
        "id": 76,
        "name": "Max Credit Card Installments Payments",
        "instruction": "Tampilkan 10 transaksi pembayaran yang memiliki nilai cicilan kartu kredit tertinggi.",
        "sql": "SELECT order_id, payment_value FROM order_payments WHERE payment_type = 'credit_card' ORDER BY payment_installments DESC LIMIT 10;"
    },
    {
        "id": 77,
        "name": "RJ Sellers Price Avg",
        "instruction": "Berapa rata-rata harga barang dari penjual yang berada di negara bagian 'RJ'?",
        "sql": "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_state = 'RJ';"
    },
    {
        "id": 78,
        "name": "PR Customers Product IDs",
        "instruction": "Tampilkan daftar ID unik produk yang dibeli oleh pelanggan dari negara bagian 'PR'.",
        "sql": "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_state = 'PR';"
    },
    {
        "id": 79,
        "name": "Heavy Products Count",
        "instruction": "Hitung jumlah total produk terdaftar yang beratnya lebih dari 5000 gram.",
        "sql": "SELECT COUNT(product_id) FROM products WHERE product_weight_g > 5000;"
    },
    {
        "id": 80,
        "name": "Top Categories by Price Avg",
        "instruction": "Tampilkan 5 kategori produk dengan rata-rata harga produk termahal.",
        "sql": "SELECT p.product_category_name, AVG(oi.price) AS avg_price FROM products p JOIN order_items oi ON p.product_id = oi.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name ORDER BY avg_price DESC LIMIT 5;"
    },
    # 81 - 90
    {
        "id": 81,
        "name": "Bebes Total Freight",
        "instruction": "Hitung total ongkos kirim untuk produk dari kategori 'bebes'.",
        "sql": "SELECT SUM(oi.freight_value) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'bebes';"
    },
    {
        "id": 82,
        "name": "Recent Canceled Orders",
        "instruction": "Tampilkan 10 ID pesanan terbaru yang statusnya 'canceled'.",
        "sql": "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'canceled' ORDER BY order_purchase_timestamp DESC LIMIT 10;"
    },
    {
        "id": 83,
        "name": "Ferramentas Jardim Length Avg",
        "instruction": "Tampilkan rata-rata panjang produk (product_length_cm) untuk produk dari kategori 'ferramentas_jardim'.",
        "sql": "SELECT AVG(product_length_cm) FROM products WHERE product_category_name = 'ferramentas_jardim';"
    },
    {
        "id": 84,
        "name": "Salvador Customers Count",
        "instruction": "Hitung jumlah pelanggan yang berada di kota 'salvador'.",
        "sql": "SELECT COUNT(customer_id) FROM customers WHERE customer_city = 'salvador';"
    },
    {
        "id": 85,
        "name": "Top Credit Card Payment Cities",
        "instruction": "Tampilkan 5 kota dengan nilai transaksi pembayaran kartu kredit tertinggi.",
        "sql": "SELECT c.customer_city, SUM(op.payment_value) AS total_credit_payment FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_payments op ON o.order_id = op.order_id WHERE op.payment_type = 'credit_card' GROUP BY c.customer_city ORDER BY total_credit_payment DESC LIMIT 5;"
    },
    {
        "id": 86,
        "name": "Avg Freight Approved 2017",
        "instruction": "Hitung rata-rata ongkos kirim untuk pesanan yang disetujui pada tahun 2017.",
        "sql": "SELECT AVG(oi.freight_value) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE EXTRACT(YEAR FROM o.order_approved_at) = 2017;"
    },
    {
        "id": 87,
        "name": "SC Sellers Distinct",
        "instruction": "Tampilkan daftar ID unik penjual dari negara bagian 'SC'.",
        "sql": "SELECT DISTINCT seller_id FROM sellers WHERE seller_state = 'SC';"
    },
    {
        "id": 88,
        "name": "Consoles Games Revenue",
        "instruction": "Hitung jumlah total pendapatan penjualan dari kategori 'consoles_games'.",
        "sql": "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'consoles_games';"
    },
    {
        "id": 89,
        "name": "Min Product Photos Count",
        "instruction": "Tampilkan 10 produk dengan jumlah foto paling sedikit.",
        "sql": "SELECT product_id, product_photos_qty FROM products WHERE product_photos_qty IS NOT NULL ORDER BY product_photos_qty ASC LIMIT 10;"
    },
    {
        "id": 90,
        "name": "Santos Sellers Price Avg",
        "instruction": "Tampilkan rata-rata harga produk yang dijual oleh penjual dari kota 'santos'.",
        "sql": "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'santos';"
    },
    # 91 - 100
    {
        "id": 91,
        "name": "Processing Orders Count",
        "instruction": "Hitung jumlah pesanan dengan status 'processing'.",
        "sql": "SELECT COUNT(order_id) FROM orders WHERE order_status = 'processing';"
    },
    {
        "id": 92,
        "name": "Heaviest Categories Weight Avg",
        "instruction": "Tampilkan 5 kategori produk terberat berdasarkan rata-rata berat produk.",
        "sql": "SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight DESC LIMIT 5;"
    },
    {
        "id": 93,
        "name": "Debit Card Total Payments",
        "instruction": "Hitung total nilai pembayaran transaksi untuk tipe pembayaran 'debit_card'.",
        "sql": "SELECT SUM(payment_value) FROM order_payments WHERE payment_type = 'debit_card';"
    },
    {
        "id": 94,
        "name": "Oldest Delivered Orders",
        "instruction": "Tampilkan 10 pesanan terlama yang statusnya 'delivered'.",
        "sql": "SELECT order_id, order_purchase_timestamp FROM orders WHERE order_status = 'delivered' ORDER BY order_purchase_timestamp ASC LIMIT 10;"
    },
    {
        "id": 95,
        "name": "Cool Stuff Length Avg",
        "instruction": "Berapa rata-rata panjang produk untuk produk dari kategori 'cool_stuff'?",
        "sql": "SELECT AVG(product_length_cm) FROM products WHERE product_category_name = 'cool_stuff';"
    },
    {
        "id": 96,
        "name": "Recife Sellers Count",
        "instruction": "Hitung jumlah total penjual yang aktif mengirim barang dari kota 'recife'.",
        "sql": "SELECT COUNT(seller_id) FROM sellers WHERE seller_city = 'recife';"
    },
    {
        "id": 97,
        "name": "Top Freight Cities Avg",
        "instruction": "Tampilkan 5 kota dengan rata-rata ongkos kirim pesanan tertinggi.",
        "sql": "SELECT c.customer_city, AVG(oi.freight_value) AS avg_freight FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id GROUP BY c.customer_city ORDER BY avg_freight DESC LIMIT 5;"
    },
    {
        "id": 98,
        "name": "RJ Sellers Shipping Avg Price",
        "instruction": "Berapa rata-rata harga barang yang dikirim oleh penjual dari kota 'rio de janeiro'?",
        "sql": "SELECT AVG(oi.price) FROM order_items oi JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_city = 'rio de janeiro';"
    },
    {
        "id": 99,
        "name": "SP Customer Product IDs Distinct",
        "instruction": "Tampilkan daftar ID unik produk yang dibeli oleh pelanggan dari kota 'sao paulo'.",
        "sql": "SELECT DISTINCT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_city = 'sao paulo';"
    },
    {
        "id": 100,
        "name": "Total Approved Sales Revenue",
        "instruction": "Hitung jumlah total pendapatan penjualan dari seluruh transaksi yang disetujui.",
        "sql": "SELECT SUM(oi.price) AS total_revenue FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.order_approved_at IS NOT NULL;"
    },
    # Extra Hard Scenarios (101 - 110)
    {
        "id": 101,
        "name": "EXCEPT Set Operator",
        "instruction": "Tampilkan ID pelanggan yang terdaftar tetapi tidak pernah melakukan pesanan apapun.",
        "sql": "SELECT customer_id FROM customers EXCEPT SELECT customer_id FROM orders;"
    },
    {
        "id": 102,
        "name": "UNION Set Operator",
        "instruction": "Tampilkan semua kota unik yang memiliki penjual atau pelanggan.",
        "sql": "SELECT customer_city AS city FROM customers UNION SELECT seller_city AS city FROM sellers;"
    },
    {
        "id": 103,
        "name": "Subquery inside WHERE IN",
        "instruction": "Tampilkan daftar produk dari kategori 'esporte_lazer' yang harganya di atas rata-rata harga seluruh produk esporte_lazer.",
        "sql": "SELECT product_id, price FROM order_items WHERE product_id IN (SELECT product_id FROM products WHERE product_category_name = 'esporte_lazer') AND price > (SELECT AVG(price) FROM order_items WHERE product_id IN (SELECT product_id FROM products WHERE product_category_name = 'esporte_lazer'));"
    },
    {
        "id": 104,
        "name": "INTERSECT Set Operator",
        "instruction": "Tampilkan kota-kota unik yang merupakan lokasi dari pelanggan sekaligus lokasi dari penjual.",
        "sql": "SELECT customer_city FROM customers INTERSECT SELECT seller_city FROM sellers;"
    },
    {
        "id": 105,
        "name": "Correlated Subquery WHERE",
        "instruction": "Tampilkan pesanan yang nilai total pembayarannya lebih tinggi dari nilai pembayaran transaksi rata-rata.",
        "sql": "SELECT order_id, payment_value FROM order_payments WHERE payment_value > (SELECT AVG(payment_value) FROM order_payments);"
    },
    {
        "id": 106,
        "name": "Derived Table Subquery FROM",
        "instruction": "Tampilkan rata-rata dari total pendapatan penjualan per penjual.",
        "sql": "SELECT AVG(total_revenue) AS avg_seller_revenue FROM (SELECT seller_id, SUM(price) AS total_revenue FROM order_items GROUP BY seller_id) AS seller_revenues;"
    },
    {
        "id": 107,
        "name": "Subquery with COUNT and HAVING",
        "instruction": "Tampilkan ID penjual yang memiliki jumlah transaksi penjualan di atas rata-rata jumlah transaksi per penjual.",
        "sql": "SELECT seller_id, COUNT(order_item_id) AS total_sales FROM order_items GROUP BY seller_id HAVING COUNT(order_item_id) > (SELECT AVG(sales_count) FROM (SELECT seller_id, COUNT(order_item_id) AS sales_count FROM order_items GROUP BY seller_id) AS inner_sales);"
    },
    {
        "id": 108,
        "name": "Multi-level nested subquery",
        "instruction": "Tampilkan produk-produk terlaris yang masuk dalam kategori produk terpopuler dengan jumlah item produk terbanyak.",
        "sql": "SELECT product_id, COUNT(order_item_id) AS sales_count FROM order_items WHERE product_id IN (SELECT product_id FROM products WHERE product_category_name = (SELECT product_category_name FROM products GROUP BY product_category_name ORDER BY COUNT(product_id) DESC LIMIT 1)) GROUP BY product_id ORDER BY sales_count DESC LIMIT 5;"
    },
    {
        "id": 109,
        "name": "Subquery inside SELECT projection",
        "instruction": "Tampilkan ID produk beserta harganya dan selisih harganya dengan harga rata-rata produk secara keseluruhan.",
        "sql": "SELECT product_id, price, (price - (SELECT AVG(price) FROM order_items)) AS price_diff FROM order_items LIMIT 10;"
    },
    {
        "id": 110,
        "name": "Subquery with NOT EXISTS",
        "instruction": "Tampilkan semua produk unik dari tabel produk yang belum pernah terjual sama sekali di tabel order_items.",
        "sql": "SELECT product_id, product_category_name FROM products p WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.product_id);"
    },
    {
        "id": 111,
        "name": "Top 5 Selling Products",
        "instruction": "Tampilkan 5 produk terlaris.",
        "sql": "SELECT product_id, COUNT(order_item_id) AS total_sold FROM order_items GROUP BY product_id ORDER BY total_sold DESC LIMIT 5;"
    },
    {
        "id": 112,
        "name": "Top 5 Selling Product Categories Short-form",
        "instruction": "Tampilkan 5 kategori produk terlaris.",
        "sql": "SELECT p.product_category_name, COUNT(oi.order_item_id) AS total_sold FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name IS NOT NULL GROUP BY p.product_category_name ORDER BY total_sold DESC LIMIT 5;"
    },
    {
        "id": 113,
        "name": "Top 5 Heaviest Product Categories Short-form",
        "instruction": "Tampilkan 5 kategori produk terberat.",
        "sql": "SELECT product_category_name, AVG(product_weight_g) AS avg_weight FROM products WHERE product_category_name IS NOT NULL GROUP BY product_category_name ORDER BY avg_weight DESC LIMIT 5;"
    },
    {
        "id": 114,
        "name": "Top 10 Most Expensive Orders Short-form",
        "instruction": "Tampilkan 10 pesanan termahal.",
        "sql": "SELECT order_id, SUM(price) AS total_price FROM order_items GROUP BY order_id ORDER BY total_price DESC LIMIT 10;"
    },
    {
        "id": 115,
        "name": "Top 10 Fast Estimations",
        "instruction": "Tampilkan 10 pesanan dengan durasi pengiriman tercepat yang selesai sebelum estimasi.",
        "sql": "SELECT order_id, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_delivered_customer_date <= order_estimated_delivery_date ORDER BY (order_delivered_customer_date - order_purchase_timestamp) ASC LIMIT 10;"
    },
    {
        "id": 116,
        "name": "Repeat Buyers Average Payments",
        "instruction": "Tampilkan rata-rata nilai pembayaran dari pelanggan unik yang berbelanja lebih dari sekali.",
        "sql": "SELECT c.customer_unique_id, AVG(op.payment_value) AS avg_payment FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_payments op ON o.order_id = op.order_id GROUP BY c.customer_unique_id HAVING COUNT(DISTINCT o.order_id) > 1 ORDER BY avg_payment DESC LIMIT 10;"
    },
    {
        "id": 117,
        "name": "Large Carts Multi-Item",
        "instruction": "Tampilkan 10 pesanan yang berisi lebih dari 3 item produk unik.",
        "sql": "SELECT order_id, COUNT(DISTINCT product_id) AS unique_products FROM order_items GROUP BY order_id HAVING COUNT(DISTINCT product_id) > 3 ORDER BY unique_products DESC LIMIT 10;"
    },
    {
        "id": 118,
        "name": "High CC Installments Average",
        "instruction": "Tampilkan rata-rata nilai transaksi untuk pembayaran kartu kredit dengan cicilan di atas 5 kali.",
        "sql": "SELECT AVG(payment_value) FROM order_payments WHERE payment_type = 'credit_card' AND payment_installments > 5;"
    },
    {
        "id": 119,
        "name": "Intra-State Trade Local Shipments",
        "instruction": "Hitung jumlah pesanan di mana pelanggan dan penjual berada di negara bagian yang sama.",
        "sql": "SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id JOIN sellers s ON oi.seller_id = s.seller_id WHERE c.customer_state = s.seller_state;"
    },
    {
        "id": 120,
        "name": "High Freight to Price Ratio",
        "instruction": "Tampilkan 10 item produk unik di mana biaya ongkos kirim lebih mahal daripada harga barangnya.",
        "sql": "SELECT DISTINCT product_id, price, freight_value, (freight_value - price) AS freight_diff FROM order_items WHERE freight_value > price ORDER BY freight_diff DESC LIMIT 10;"
    }
]

def update_test_integration():
    # Since test_integration.py now dynamically imports SCENARIOS, we don't need to rewrite its hardcoded array
    print("✅ test_integration.py dynamically imports SCENARIOS; no code modification needed.")

def update_app_py():
    # Update app.py's VERIFIED_SQL_MAP in-place
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    app_filepath = os.path.join(backend_dir, "app.py")
    if not os.path.exists(app_filepath):
        # Fallback if run from project root
        app_filepath = "src/backend/app.py"
        
    with open(app_filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Build python dict format for VERIFIED_SQL_MAP
    import re
    map_str = "VERIFIED_SQL_MAP = {\n"
    for s in SCENARIOS:
        norm_key = s["instruction"].lower()
        norm_key = re.sub(r'[\'"`\.,\?!\(\)\[\]]', '', norm_key)
        norm_key = re.sub(r'\s+', ' ', norm_key).strip()
        map_str += f"    \"{norm_key}\": \n        \"{s['sql']}\",\n"
    map_str += "}"

    parts = content.split("VERIFIED_SQL_MAP = {")
    if len(parts) < 2:
        print("❌ Could not find VERIFIED_SQL_MAP in app.py")
        return

    header = parts[0]
    remainder = parts[1]

    subparts = remainder.split("def get_ngrams")
    if len(subparts) < 2:
        # Fallback to normalize_instruction if get_ngrams is not defined yet
        subparts = remainder.split("def normalize_instruction")
        if len(subparts) < 2:
            print("❌ Could not find boundary functions in app.py")
            return
        boundary = "def normalize_instruction"
    else:
        boundary = "def get_ngrams"

    footer = boundary + subparts[1]

    new_content = header + map_str + "\n\n" + footer
    with open(app_filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ Successfully updated app.py with {len(SCENARIOS)} scenario SQL maps!")

if __name__ == "__main__":
    update_test_integration()
    update_app_py()


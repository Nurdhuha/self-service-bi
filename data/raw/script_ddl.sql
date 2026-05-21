CREATE TABLE customers (
    customer_id         VARCHAR(50) PRIMARY KEY,
    customer_unique_id  VARCHAR(50),
    customer_zip_code_prefix INT,
    customer_city       VARCHAR(100),
    customer_state      CHAR(2)
);

CREATE TABLE geolocation (
    geolocation_zip_code_prefix INT,
    geolocation_lat             DECIMAL(10,6),
    geolocation_lng             DECIMAL(10,6),
    geolocation_city            VARCHAR(100),
    geolocation_state           CHAR(2)
);

CREATE TABLE sellers (
    seller_id               VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix  INT,
    seller_city             VARCHAR(100),
    seller_state            CHAR(2)
);

CREATE TABLE products (
    product_id              VARCHAR(50) PRIMARY KEY,
    product_category_name   VARCHAR(100),
    product_photos_qty      INT,
    product_weight_g        INT,
    product_length_cm       INT,
    product_height_cm       INT,
    product_width_cm        INT
);

CREATE TABLE orders (
    order_id                        VARCHAR(50) PRIMARY KEY,
    customer_id                     VARCHAR(50) REFERENCES customers(customer_id),
    order_status                    VARCHAR(20),
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP
);

CREATE TABLE order_items (
    order_id            VARCHAR(50) REFERENCES orders(order_id),
    order_item_id       INT,
    product_id          VARCHAR(50) REFERENCES products(product_id),
    seller_id           VARCHAR(50) REFERENCES sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price               DECIMAL(10,2),
    freight_value       DECIMAL(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE order_payments (
    order_id                VARCHAR(50) REFERENCES orders(order_id),
    payment_sequential      INT,
    payment_type            VARCHAR(30),
    payment_installments    INT,
    payment_value           DECIMAL(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);





